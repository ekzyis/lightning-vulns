"""GitHub pull requests, issues, security advisories and releases.

Always goes through api.github.com — the JSON is cleaner and more stable than
the rendered HTML. Set GITHUB_TOKEN to lift the 60 requests/hour anonymous cap.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..fetch import Fetcher, github_headers
from ..render import find_cves, first_paragraph, parse_date, squash, tidy
from .base import Record

API = "https://api.github.com"

PATTERNS = [
    ("pr", re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<ref>\d+)")),
    ("issue", re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<ref>\d+)")),
    ("security-advisory", re.compile(
        r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/security/advisories/(?P<ref>GHSA-[\w-]+)")),
    ("release", re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/releases/tag/(?P<ref>[^/]+)")),
    ("commit", re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/commit/(?P<ref>[0-9a-f]{7,40})")),
]


class GitHubAdapter:
    site = "github"

    def matches(self, url: str) -> bool:
        return urlsplit(url).netloc == "github.com" and _classify(url) is not None

    def parse(self, url: str, fetcher: Fetcher) -> Record:
        kind, owner, repo, ref = _classify(url)
        endpoint = {
            "pr": f"{API}/repos/{owner}/{repo}/pulls/{ref}",
            "issue": f"{API}/repos/{owner}/{repo}/issues/{ref}",
            "security-advisory": f"{API}/repos/{owner}/{repo}/security-advisories/{ref}",
            "release": f"{API}/repos/{owner}/{repo}/releases/tags/{ref}",
            "commit": f"{API}/repos/{owner}/{repo}/commits/{ref}",
        }[kind]

        data = fetcher.get(endpoint, headers=github_headers()).json()
        build = {
            "pr": _pull_request,
            "issue": _issue,
            "security-advisory": _advisory,
            "release": _release,
            "commit": _commit,
        }[kind]

        record = build(data)
        record.url = url
        record.site = self.site
        record.kind = f"github-{kind}"
        record.canonical_url = record.canonical_url or data.get("html_url") or url
        record.extra.setdefault("repo", f"{owner}/{repo}")
        record.extra.setdefault("ref", ref)
        record.summary = record.summary or first_paragraph(record.body_markdown)
        record.cves = record.cves or find_cves(record.title, record.body_markdown)
        return record


def _classify(url: str):
    path = urlsplit(url).path
    for kind, pattern in PATTERNS:
        match = pattern.match(path)
        if match:
            return kind, match["owner"], match["repo"], match["ref"]
    return None


def _pull_request(data: dict) -> Record:
    return Record(
        url="", site="", kind="",
        title=squash(data.get("title")),
        authors=[(data.get("user") or {}).get("login", "")],
        published=parse_date(data.get("created_at")),
        updated=parse_date(data.get("merged_at") or data.get("closed_at") or data.get("updated_at")),
        body_markdown=tidy(data.get("body") or ""),
        extra={
            "state": data.get("state"),
            "merged": data.get("merged"),
            "merged_at": parse_date(data.get("merged_at")),
            "base": (data.get("base") or {}).get("ref"),
            "changed_files": data.get("changed_files"),
        },
    )


def _issue(data: dict) -> Record:
    return Record(
        url="", site="", kind="",
        title=squash(data.get("title")),
        authors=[(data.get("user") or {}).get("login", "")],
        published=parse_date(data.get("created_at")),
        updated=parse_date(data.get("closed_at") or data.get("updated_at")),
        body_markdown=tidy(data.get("body") or ""),
        extra={
            "state": data.get("state"),
            "labels": [lbl.get("name") for lbl in data.get("labels") or []],
            "comments": data.get("comments"),
        },
    )


def _advisory(data: dict) -> Record:
    vulns = data.get("vulnerabilities") or []
    return Record(
        url="", site="", kind="",
        title=squash(data.get("summary")),
        authors=[(data.get("publisher") or {}).get("login", "")],
        published=parse_date(data.get("published_at")),
        updated=parse_date(data.get("updated_at")),
        body_markdown=tidy(data.get("description") or ""),
        cves=[data["cve_id"]] if data.get("cve_id") else [],
        links=[ref for ref in data.get("references") or [] if isinstance(ref, str)],
        extra={
            "ghsa_id": data.get("ghsa_id"),
            "severity": data.get("severity"),
            "cvss": (data.get("cvss") or {}).get("score"),
            "cvss_vector": (data.get("cvss") or {}).get("vector_string"),
            "cwes": [c.get("cwe_id") for c in data.get("cwes") or []],
            "affected": [
                {
                    "package": (v.get("package") or {}).get("name"),
                    "ecosystem": (v.get("package") or {}).get("ecosystem"),
                    "vulnerable_range": v.get("vulnerable_version_range"),
                    "patched": v.get("patched_versions"),
                }
                for v in vulns
            ],
        },
    )


def _release(data: dict) -> Record:
    return Record(
        url="", site="", kind="",
        title=squash(data.get("name") or data.get("tag_name")),
        authors=[(data.get("author") or {}).get("login", "")],
        published=parse_date(data.get("published_at")),
        body_markdown=tidy(data.get("body") or ""),
        extra={"tag": data.get("tag_name"), "prerelease": data.get("prerelease")},
    )


def _commit(data: dict) -> Record:
    commit = data.get("commit") or {}
    message = commit.get("message") or ""
    return Record(
        url="", site="", kind="",
        title=squash(message.split("\n")[0]),
        authors=[(commit.get("author") or {}).get("name", "")],
        published=parse_date((commit.get("author") or {}).get("date")),
        body_markdown=tidy(message),
        extra={"sha": data.get("sha"), "stats": data.get("stats")},
    )
