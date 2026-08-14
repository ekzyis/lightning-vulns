"""The record every adapter produces, and the adapter protocol."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Protocol

from ..fetch import Fetcher


@dataclass
class Record:
    """One scraped source, normalised across every site we support."""

    url: str                       # the URL as referenced from README.md
    site: str                      # short site id, e.g. "delvingbitcoin"
    kind: str                      # advisory | blog | forum | pr | issue | ...
    title: str = ""
    canonical_url: str = ""
    authors: list[str] = field(default_factory=list)
    published: str | None = None   # ISO date
    updated: str | None = None     # ISO date
    summary: str = ""
    body_markdown: str = ""
    cves: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["canonical_url"] = self.canonical_url or self.url
        # Lets a later run tell "content actually changed" from "re-fetched".
        data["content_sha256"] = hashlib.sha256(
            self.body_markdown.encode("utf-8")
        ).hexdigest()
        return data


class Adapter(Protocol):
    site: str

    def matches(self, url: str) -> bool: ...

    def parse(self, url: str, fetcher: Fetcher) -> Record: ...
