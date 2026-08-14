"""Work out which URLs to scrape.

Two jobs:

1. Parse README.md into its advisory entries, so every scraped source stays
   attributed to the vulnerability it documents.
2. Ask the sites that publish an index (currently only Lightning Labs) what
   they have, so newly published advisories show up as pending work rather
   than being noticed by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .adapters import lightning_community
from .fetch import Fetcher
from .render import find_cves, squash

HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.M)
REFERENCE_RE = re.compile(r"^-\s+(?P<url>https?://\S+)\s*$", re.M)
FIELD_RE = r"^\*\*{name}\*\*:\s*(?P<value>.+?)\s*$"


@dataclass
class Entry:
    """One `## ...` section of README.md."""

    title: str
    slug: str
    disclosure: str | None = None
    patched: str | None = None
    cves: list[str] = field(default_factory=list)
    summary: str = ""
    references: list[str] = field(default_factory=list)


def slugify(title: str) -> str:
    """Match the anchor scheme index.sh already uses."""
    return re.sub(r"[^a-z0-9_]+", "-", title.lower())


def parse_readme(path: Path) -> list[Entry]:
    text = Path(path).read_text(encoding="utf-8")
    headings = list(HEADING_RE.finditer(text))
    entries: list[Entry] = []

    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[match.end():end]
        title = squash(match.group("title"))

        entries.append(
            Entry(
                title=title,
                slug=slugify(title),
                disclosure=_field(section, "Disclosure"),
                patched=_field(section, "Patched"),
                cves=find_cves(section),
                summary=_blockquote(section),
                references=REFERENCE_RE.findall(section),
            )
        )
    return entries


def _field(section: str, name: str) -> str | None:
    match = re.search(FIELD_RE.format(name=name), section, re.M)
    return squash(match.group("value")) if match else None


def _blockquote(section: str) -> str:
    lines = [
        line[1:].strip() if line.startswith(">") else ""
        for line in section.splitlines()
        if line.startswith(">") or not line.strip()
    ]
    return squash(" ".join(lines))


def known_urls(entries: list[Entry]) -> list[str]:
    """Every referenced URL, de-duplicated, in README order."""
    urls: list[str] = []
    for entry in entries:
        for url in entry.references:
            if url not in urls:
                urls.append(url)
    return urls


# Advisory hosts publish the same content under two domains; treat them as one
# when checking whether a discovered URL is already covered.
HOST_ALIASES = {"security.lightning.engineering": "lightning.community"}


def _fingerprint(url: str) -> str:
    """A comparison key that ignores host aliases, /SI/ prefixes and .html."""
    url = re.sub(r"^https?://", "", url).rstrip("/")
    host, _, path = url.partition("/")
    host = HOST_ALIASES.get(host, host)
    path = re.sub(r"^SI/", "", path)
    path = re.sub(r"\.html$", "", path)
    return f"{host}/{path}"


def find_new(fetcher: Fetcher, entries: list[Entry]) -> list[str]:
    """Advisories published upstream that README.md does not reference yet."""
    covered = {_fingerprint(u) for u in known_urls(entries)}
    try:
        published = lightning_community.index_urls(fetcher)
    except Exception:
        return []
    return [u for u in published if _fingerprint(u) not in covered]
