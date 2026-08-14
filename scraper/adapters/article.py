"""Generic article/blog adapter.

Covers morehouse.github.io and nishantbansal2003.github.io today, and is the
fallback for any HTML source without a dedicated adapter. It leans on
OpenGraph metadata plus the usual Jekyll/Hugo content containers.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from ..fetch import Fetcher
from ..render import (
    find_cves,
    first_paragraph,
    html_to_markdown,
    meta,
    outbound_links,
    parse_date,
    soup,
    squash,
)
from .base import Record

CONTENT_SELECTORS = [
    ".entry-content",
    ".post-content",
    ".article-content",
    "article .content",
    "article",
    "main",
]

SITE_IDS = {
    "morehouse.github.io": "morehouse",
    "nishantbansal2003.github.io": "nishantbansal",
    "bitcoinops.org": "bitcoinops",
}


class ArticleAdapter:
    site = "article"

    def matches(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def parse(self, url: str, fetcher: Fetcher) -> Record:
        resp = fetcher.get(url)
        page = soup(resp.text)
        host = urlsplit(url).netloc

        content = next(
            (page.select_one(sel) for sel in CONTENT_SELECTORS if page.select_one(sel)),
            page.body or page,
        )
        body = html_to_markdown(content, base_url=url)

        title = meta(page, "og:title", "twitter:title")
        if not title:
            heading = content.find("h1") or page.find("h1")
            title = squash(heading.get_text()) if heading else squash(
                page.title.get_text() if page.title else ""
            )

        published = parse_date(meta(page, "article:published_time", "date", "dc.date"))
        if not published:
            time_el = page.find("time")
            if time_el:
                published = parse_date(time_el.get("datetime") or time_el.get_text())

        summary = meta(page, "og:description", "description") or first_paragraph(body)

        return Record(
            url=url,
            site=SITE_IDS.get(host, host),
            kind="blog",
            title=title,
            canonical_url=_canonical(page, url),
            authors=_authors(page),
            published=published,
            updated=parse_date(meta(page, "article:modified_time")),
            summary=summary,
            body_markdown=body,
            cves=find_cves(title, body),
            links=outbound_links(content, url),
            extra={"tags": _tags(page)},
        )


def _authors(page) -> list[str]:
    for sel in [".author", '[rel="author"]', ".post-author", ".byline"]:
        el = page.select_one(sel)
        if el:
            name = squash(el.get_text())
            if name:
                return [name]
    name = meta(page, "author", "article:author")
    return [name] if name else []


def _tags(page) -> list[str]:
    tags = []
    for el in page.select('a[rel="tag"], .tag, .post-tags a, .tags a'):
        tag = squash(el.get_text())
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _canonical(page, url: str) -> str:
    link = page.find("link", rel=lambda v: v and "canonical" in v)
    return link["href"] if link and link.get("href") else url
