"""Delving Bitcoin (Discourse).

Discourse exposes every topic as JSON by appending ``.json``, which gives us
the whole thread rather than the first few posts the HTML renders.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..fetch import Fetcher
from ..render import find_cves, first_paragraph, html_to_markdown, parse_date, squash
from .base import Record

TOPIC_RE = re.compile(r"^/t/(?P<slug>[^/]+)/(?P<topic_id>\d+)")

# Replies past this point are usually discussion, not disclosure content.
MAX_POSTS = 20


class DiscourseAdapter:
    site = "delvingbitcoin"

    def matches(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.netloc == "delvingbitcoin.org" and bool(TOPIC_RE.match(parts.path))

    def parse(self, url: str, fetcher: Fetcher) -> Record:
        parts = urlsplit(url)
        match = TOPIC_RE.match(parts.path)
        topic_id = match.group("topic_id")
        api = f"{parts.scheme}://{parts.netloc}/t/{topic_id}.json"

        topic = fetcher.get(api).json()
        posts = topic.get("post_stream", {}).get("posts", [])[:MAX_POSTS]

        rendered = []
        authors: list[str] = []
        links: list[str] = []
        for post in posts:
            author = post.get("username") or ""
            if author and author not in authors:
                authors.append(author)
            body = html_to_markdown(post.get("cooked", ""), base_url=url)
            when = parse_date(post.get("created_at")) or ""
            rendered.append(f"### #{post.get('post_number')} — {author} ({when})\n\n{body}")
            for link in post.get("link_counts") or []:
                href = link.get("url")
                if href and href.startswith("http") and href not in links:
                    links.append(href)

        body_markdown = "\n\n".join(rendered)
        first_post = html_to_markdown(posts[0].get("cooked", ""), base_url=url) if posts else ""

        return Record(
            url=url,
            site=self.site,
            kind="forum",
            title=squash(topic.get("title")),
            canonical_url=f"{parts.scheme}://{parts.netloc}/t/{topic.get('slug')}/{topic_id}",
            authors=authors,
            published=parse_date(topic.get("created_at")),
            updated=parse_date(topic.get("last_posted_at")),
            summary=first_paragraph(first_post),
            body_markdown=body_markdown,
            cves=find_cves(topic.get("title", ""), body_markdown),
            links=links,
            extra={
                "topic_id": int(topic_id),
                "posts_total": topic.get("posts_count"),
                "posts_scraped": len(posts),
                "tags": [t["name"] if isinstance(t, dict) else t for t in topic.get("tags") or []],
            },
        )
