"""Adapter registry.

Order matters: the first adapter whose ``matches()`` returns True wins, and
ArticleAdapter matches everything, so it stays last.
"""

from __future__ import annotations

from ..fetch import Fetcher
from .article import ArticleAdapter
from .base import Record
from .discourse import DiscourseAdapter
from .github import GitHubAdapter
from .lightning_community import LightningCommunityAdapter
from .mailing_list import MailingListAdapter

ADAPTERS = [
    LightningCommunityAdapter(),
    DiscourseAdapter(),
    GitHubAdapter(),
    MailingListAdapter(),
    ArticleAdapter(),
]


def for_url(url: str):
    for adapter in ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


def scrape(url: str, fetcher: Fetcher) -> Record:
    adapter = for_url(url)
    if adapter is None:
        raise ValueError(f"no adapter for {url}")
    return adapter.parse(url, fetcher)


__all__ = ["ADAPTERS", "Record", "for_url", "scrape"]
