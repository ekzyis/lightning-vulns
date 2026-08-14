"""Cached, rate-limited HTTP fetching.

Every response is cached on disk so that re-runs are cheap and the upstream
hosts only see a conditional request (If-None-Match / If-Modified-Since) at
most once per run per URL.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

USER_AGENT = (
    "lightning-vulns-scraper/0.1 "
    "(+https://github.com/ekzyis/lightning-vulns)"
)

# Minimum seconds between two requests to the same host.
HOST_DELAY = 1.0

RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class Response:
    url: str
    final_url: str
    status: int
    headers: dict
    text: str
    from_cache: bool

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def json(self):
        return json.loads(self.text)


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


class Fetcher:
    def __init__(self, cache_dir: Path, offline: bool = False, refresh: bool = False):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.refresh = refresh
        self._last_hit: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT

    # -- cache ------------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{_key(url)}.json"

    def _read_cache(self, url: str) -> dict | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, url: str, entry: dict) -> None:
        path = self._cache_path(url)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        tmp.replace(path)

    # -- fetching ---------------------------------------------------------

    def _throttle(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_hit.get(host)
        if last is not None:
            wait = HOST_DELAY - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, headers: dict | None = None, tries: int = 4) -> Response:
        cached = self._read_cache(url)

        if self.offline:
            if cached is None:
                raise LookupError(f"offline and not cached: {url}")
            return self._from_cache(url, cached)

        if cached is not None and not self.refresh:
            # Still revalidate, but a 304 costs the server almost nothing.
            pass

        req_headers = dict(headers or {})
        if cached and not self.refresh:
            if cached.get("etag"):
                req_headers["If-None-Match"] = cached["etag"]
            if cached.get("last_modified"):
                req_headers["If-Modified-Since"] = cached["last_modified"]

        last_error: Exception | None = None
        for attempt in range(tries):
            self._throttle(url)
            try:
                resp = self._session.get(url, headers=req_headers, timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(2**attempt)
                continue

            if resp.status_code == 304 and cached:
                return self._from_cache(url, cached)

            if resp.status_code in RETRY_STATUS and attempt < tries - 1:
                delay = float(resp.headers.get("Retry-After") or 2**attempt)
                time.sleep(min(delay, 60))
                continue

            if resp.status_code >= 400:
                raise FetchError(url, resp.status_code, resp.text[:400])

            entry = {
                "url": url,
                "final_url": resp.url,
                "status": resp.status_code,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "content_type": resp.headers.get("Content-Type", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "body": resp.text,
            }
            self._write_cache(url, entry)
            return Response(
                url=url,
                final_url=resp.url,
                status=resp.status_code,
                headers=dict(resp.headers),
                text=resp.text,
                from_cache=False,
            )

        if cached is not None:
            return self._from_cache(url, cached)
        raise FetchError(url, 0, str(last_error))

    @staticmethod
    def _from_cache(url: str, entry: dict) -> Response:
        return Response(
            url=url,
            final_url=entry.get("final_url", url),
            status=entry.get("status", 200),
            headers={"Content-Type": entry.get("content_type", "")},
            text=entry.get("body", ""),
            from_cache=True,
        )


class FetchError(RuntimeError):
    def __init__(self, url: str, status: int, detail: str = ""):
        self.url = url
        self.status = status
        self.detail = detail
        super().__init__(f"{status or 'ERR'} fetching {url}: {detail.strip()[:200]}")


def github_headers() -> dict:
    """Auth headers for api.github.com when a token is available.

    Unauthenticated works but is capped at 60 requests/hour, which is not
    enough to refresh every GitHub reference in one run.
    """
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
