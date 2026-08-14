"""lightning-dev mailing list posts.

Both the Linux Foundation pipermail archive and the diyhpl.us mirror serve a
raw RFC822 message, so one parser covers both.
"""

from __future__ import annotations

import email
import re
from urllib.parse import urlsplit

from ..fetch import Fetcher
from ..render import find_cves, first_paragraph, parse_date, squash, tidy
from .base import Record

HOSTS = {
    "lists.linuxfoundation.org": "lightning-dev-pipermail",
    "diyhpl.us": "lightning-dev-mirror",
}

# pipermail obfuscates addresses as "user at example.com"
FROM_RE = re.compile(r"^(?P<addr>\S+ at \S+)\s*(?:\((?P<name>[^)]+)\))?")


class MailingListAdapter:
    site = "mailing-list"

    def matches(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.netloc in HOSTS and "pipermail" in parts.path

    def parse(self, url: str, fetcher: Fetcher) -> Record:
        resp = fetcher.get(url)
        message = email.message_from_string(resp.text)

        body = message.get_payload()
        if isinstance(body, list):
            body = "\n\n".join(str(part.get_payload()) for part in body)

        subject = squash(message.get("Subject", ""))
        subject = re.sub(r"^\[[^\]]+\]\s*", "", subject)  # drop the [Lightning-dev] tag

        name, addr = _sender(message)
        body_markdown = tidy(_strip_signature(body or ""))

        return Record(
            url=url,
            site=HOSTS[urlsplit(url).netloc],
            kind="mailing-list",
            title=subject,
            canonical_url=url,
            authors=[name] if name else ([addr] if addr else []),
            published=parse_date(message.get("Date")),
            summary=first_paragraph(body_markdown),
            body_markdown=body_markdown,
            cves=find_cves(subject, body_markdown),
            links=sorted(set(re.findall(r"https?://[^\s<>()\[\]]+", body_markdown))),
            extra={
                "list": "lightning-dev",
                "message_id": squash(message.get("Message-ID", "")).strip("<>") or None,
                "from": addr,
            },
        )


def _sender(message) -> tuple[str | None, str | None]:
    raw = squash(message.get("From", ""))
    match = FROM_RE.match(raw)
    if match:
        return match.group("name"), match.group("addr")
    return None, raw or None


def _strip_signature(body: str) -> str:
    """Cut the mailman footer, which is identical on every post."""
    for marker in ("\n_______________________________________________\n", "\n-- \n"):
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx]
    return body
