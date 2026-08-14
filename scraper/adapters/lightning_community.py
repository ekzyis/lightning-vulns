"""Lightning Labs security advisories.

Published at both lightning.community/SI/ and security.lightning.engineering.
These pages are the richest source we have: severity tier, CVSS, affected and
patched versions and both fix and disclosure dates are all marked up.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..fetch import Fetcher
from ..render import (
    find_cves,
    first_paragraph,
    html_to_markdown,
    outbound_links,
    parse_date,
    soup,
    squash,
)
from .base import Record

HOSTS = {"lightning.community", "security.lightning.engineering"}


class LightningCommunityAdapter:
    site = "lightning-labs-advisories"

    def matches(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.netloc not in HOSTS:
            return False
        return parts.netloc == "security.lightning.engineering" or parts.path.startswith("/SI/")

    def parse(self, url: str, fetcher: Fetcher) -> Record:
        resp = fetcher.get(url)
        page = soup(resp.text)
        article = page.select_one("article.advisory") or page.select_one("article") or page

        title_el = article.select_one(".advisory__title") or article.find("h1")
        title = squash(title_el.get_text()) if title_el else ""

        details = _detail_list(article)
        content = article.select_one(".advisory__content") or article
        body = html_to_markdown(content, base_url=url)

        published_el = article.select_one(".advisory__published")
        published = parse_date(details.get("Disclosure Date")) or parse_date(
            squash(published_el.get_text()) if published_el else None
        )

        extra = {
            "severity": details.get("Severity"),
            "product": details.get("Product"),
            "affected_versions": details.get("Affected"),
            "patched_versions": details.get("Patched"),
            "cvss": details.get("CVSS"),
            "cvss_vector": details.get("CVSS Vector"),
            "fix_date": parse_date(details.get("Fix Date")),
            "products": _summary_table(article),
        }

        return Record(
            url=url,
            site=self.site,
            kind="advisory",
            title=title,
            canonical_url=_canonical(page, url),
            authors=["Lightning Labs"],
            published=published,
            summary=first_paragraph(body),
            body_markdown=body,
            cves=find_cves(details.get("CVE ID", ""), body),
            links=outbound_links(content, url),
            extra={k: v for k, v in extra.items() if v},
        )


def _detail_list(article) -> dict[str, str]:
    """The 'Advisory Details' sidebar, as a plain dict."""
    out: dict[str, str] = {}
    for row in article.select(".detail-list__row"):
        key = row.find("dt")
        val = row.find("dd")
        if key and val:
            out[squash(key.get_text())] = squash(val.get_text(" "))
    return out


def _summary_table(article) -> list[dict]:
    """The affected/patched matrix; some advisories list several products."""
    table = article.select_one("table.summary-table")
    if not table:
        return []
    headers = [squash(th.get_text()) for th in table.select("th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [squash(td.get_text()) for td in tr.select("td")]
        if cells:
            rows.append(dict(zip(headers, cells)))
    return rows


def _canonical(page, url: str) -> str:
    link = page.find("link", rel=lambda v: v and "canonical" in v)
    if link and link.get("href"):
        return link["href"]
    return url


def index_urls(fetcher: Fetcher) -> list[str]:
    """Every advisory linked from the Atom feed — used to spot new ones."""
    resp = fetcher.get("https://lightning.community/SI/feed.xml")
    found = re.findall(r'<link[^>]+href="([^"]+)"[^>]*rel="alternate"', resp.text)
    return [u for u in dict.fromkeys(found) if re.search(r"/\d{4}/\d{2}/\d{2}/", u)]
