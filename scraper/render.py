"""HTML -> Markdown, plus the small text helpers the adapters share."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

# Wrappers that never carry advisory content.
NOISE_SELECTORS = [
    "script", "style", "noscript", "nav", "footer", "form",
    ".sharing", ".share", ".related", ".comments", "#comments",
    ".post-nav", ".pagination", ".site-header", ".site-footer",
]


def soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # lxml not installed
        return BeautifulSoup(html, "html.parser")


class _Converter(MarkdownConverter):
    """Fenced code blocks, ATX headings, '-' bullets."""

    def convert_pre(self, el, text, parent_tags=None):
        if not text:
            return ""
        lang = ""
        classes = (el.get("class") or []) + ((el.code or {}).get("class", []) if el.code else [])
        for cls in classes:
            match = re.match(r"(?:language-|lang-|highlight-)(\w+)", str(cls))
            if match:
                lang = match.group(1)
                break
        return f"\n\n```{lang}\n{text.strip()}\n```\n\n"


def html_to_markdown(node, base_url: str = "") -> str:
    """Convert a BeautifulSoup node (or HTML string) to Markdown."""
    if isinstance(node, str):
        node = soup(node)
    else:
        node = soup(str(node))

    for sel in NOISE_SELECTORS:
        for el in node.select(sel):
            el.decompose()

    if base_url:
        for tag, attr in (("a", "href"), ("img", "src")):
            for el in node.find_all(tag):
                val = el.get(attr)
                if val and not val.startswith(("http://", "https://", "data:", "mailto:", "#")):
                    el[attr] = urljoin(base_url, val)

    md = _Converter(heading_style="ATX", bullets="-", code_language="").convert_soup(node)
    return tidy(md)


def tidy(text: str) -> str:
    """Collapse the ragged whitespace markdownify leaves behind."""
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def squash(text: str | None) -> str:
    """One-line whitespace normalisation, for titles and summaries."""
    return re.sub(r"\s+", " ", text or "").strip()


def first_paragraph(markdown: str, limit: int = 400, min_length: int = 40) -> str:
    """A short summary taken from the first substantial paragraph of a body."""
    fallback = ""
    for block in markdown.split("\n\n"):
        lines = block.strip().splitlines()
        # Setext heading ("Problem" over "-------"): the title, not the prose.
        if len(lines) >= 2 and re.fullmatch(r"[-=]{2,}", lines[1].strip()):
            continue
        block = squash(block)
        if not block or block.startswith(("#", "!", "|", "```", ">", "-", "*")):
            continue
        if len(block) < min_length:  # a greeting or a stray caption
            fallback = fallback or block
            continue
        return block if len(block) <= limit else block[:limit].rsplit(" ", 1)[0] + "…"
    return fallback


# -- dates ----------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%a, %d %b %Y %H:%M:%S %z",
]


def parse_date(value: str | None) -> str | None:
    """Normalise a date-ish string to ISO ``YYYY-MM-DD``, or None."""
    value = squash(value)
    if not value:
        return None

    iso = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso).date().isoformat()
    except ValueError:
        pass

    cleaned = re.sub(r"^(Published|Updated|Disclosed|Posted)\s+", "", value, flags=re.I)
    cleaned = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", cleaned)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue

    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", value)
    if match:
        return match.group(0)
    return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -- misc extraction ------------------------------------------------------

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")


def find_cves(*texts: str) -> list[str]:
    found: list[str] = []
    for text in texts:
        for cve in CVE_RE.findall(text or ""):
            if cve not in found:
                found.append(cve)
    return found


def meta(page: BeautifulSoup, *names: str) -> str | None:
    """Read the first matching <meta property=...> / <meta name=...>."""
    for name in names:
        el = page.find("meta", attrs={"property": name}) or page.find("meta", attrs={"name": name})
        if el and el.get("content"):
            return squash(el["content"])
    return None


def outbound_links(node, base_url: str = "") -> list[str]:
    """Absolute http(s) links inside a node, de-duplicated, order preserved."""
    links: list[str] = []
    for a in node.find_all("a", href=True):
        href = urljoin(base_url, a["href"]) if base_url else a["href"]
        if href.startswith(("http://", "https://")) and href not in links:
            links.append(href)
    return links
