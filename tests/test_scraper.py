"""Offline tests: every fetch is served from tests/fixtures, never the network.

    python3 -m unittest discover tests
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

from scraper import discover, render  # noqa: E402
from scraper.adapters import for_url  # noqa: E402
from scraper.adapters.discourse import DiscourseAdapter  # noqa: E402
from scraper.adapters.github import GitHubAdapter, _classify  # noqa: E402
from scraper.adapters.lightning_community import LightningCommunityAdapter  # noqa: E402
from scraper.adapters.mailing_list import MailingListAdapter  # noqa: E402
from scraper.fetch import Response  # noqa: E402


class StubFetcher:
    """Returns canned bodies keyed by URL; fails loudly on anything else."""

    def __init__(self, bodies: dict[str, str]):
        self.bodies = bodies
        self.requested: list[str] = []

    def get(self, url: str, headers=None, tries: int = 1) -> Response:
        self.requested.append(url)
        if url not in self.bodies:
            raise AssertionError(f"unexpected request: {url}")
        return Response(url, url, 200, {}, self.bodies[url], from_cache=True)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class LightningCommunityTests(unittest.TestCase):
    url = "https://lightning.community/SI/2024/06/20/lnd-onion-bomb.html"

    def setUp(self):
        fetcher = StubFetcher({self.url: fixture("lightning_community_advisory.html")})
        self.record = LightningCommunityAdapter().parse(self.url, fetcher)

    def test_core_fields(self):
        self.assertEqual(self.record.title, "LND Onion Bomb")
        self.assertEqual(self.record.kind, "advisory")
        self.assertEqual(self.record.published, "2024-06-20")
        self.assertEqual(self.record.cves, ["CVE-2024-38359"])

    def test_structured_details(self):
        extra = self.record.extra
        self.assertEqual(extra["product"], "lnd")
        self.assertEqual(extra["affected_versions"], "< 0.17.0-beta")
        self.assertEqual(extra["patched_versions"], "0.17.0-beta")
        self.assertEqual(extra["cvss"], "7.5/10")
        self.assertEqual(extra["fix_date"], "2023-10-03")
        self.assertEqual(len(extra["products"]), 1)

    def test_body_is_markdown_with_absolute_links(self):
        body = self.record.body_markdown
        self.assertIn("## Impact", body)
        self.assertNotIn("<p>", body)
        self.assertIn("https://github.com/lightningnetwork/lnd/releases/tag/v0.17.0-beta", body)


class DiscourseTests(unittest.TestCase):
    url = "https://delvingbitcoin.org/t/dos-disclosure-lnd-onion-bomb/979"
    api = "https://delvingbitcoin.org/t/979.json"

    def setUp(self):
        fetcher = StubFetcher({self.api: fixture("discourse_topic.json")})
        self.fetcher = fetcher
        self.record = DiscourseAdapter().parse(self.url, fetcher)

    def test_uses_the_json_api_not_the_html(self):
        self.assertEqual(self.fetcher.requested, [self.api])

    def test_core_fields(self):
        self.assertEqual(self.record.title, "DoS Disclosure: LND Onion Bomb")
        self.assertEqual(self.record.published, "2024-06-18")
        self.assertEqual(self.record.authors[0], "morehouse")
        self.assertEqual(self.record.extra["tags"], ["lightning"])

    def test_thread_is_flattened_with_post_headers(self):
        self.assertIn("### #1 — morehouse", self.record.body_markdown)
        self.assertEqual(self.record.extra["posts_scraped"], 2)


class MailingListTests(unittest.TestCase):
    url = "https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-September/002174.html"

    def setUp(self):
        fetcher = StubFetcher({self.url: fixture("pipermail_message.txt")})
        self.record = MailingListAdapter().parse(self.url, fetcher)

    def test_headers_are_parsed(self):
        self.assertEqual(
            self.record.title,
            "Full Disclosure: CVE-2019-12998 / CVE-2019-12999 / CVE-2019-13000",
        )
        self.assertEqual(self.record.authors, ["Rusty Russell"])
        self.assertEqual(self.record.published, "2019-09-27")

    def test_all_three_cves_found(self):
        self.assertEqual(
            self.record.cves, ["CVE-2019-12998", "CVE-2019-12999", "CVE-2019-13000"]
        )

    def test_summary_skips_the_setext_heading(self):
        self.assertTrue(self.record.summary.startswith("A lightning node accepting a channel"))

    def test_mailman_footer_is_stripped(self):
        self.assertNotIn("Lightning-dev mailing list", self.record.body_markdown)


class GitHubRoutingTests(unittest.TestCase):
    cases = [
        ("https://github.com/lightningnetwork/lnd/pull/9068", "pr", "9068"),
        ("https://github.com/lightningnetwork/lnd/issues/7096", "issue", "7096"),
        (
            "https://github.com/btcsuite/btcd/security/advisories/GHSA-27vh-h6mc-q6g8",
            "security-advisory",
            "GHSA-27vh-h6mc-q6g8",
        ),
        (
            "https://github.com/lightningnetwork/lnd/releases/tag/v0.15.4-beta",
            "release",
            "v0.15.4-beta",
        ),
    ]

    def test_classification(self):
        for url, kind, ref in self.cases:
            with self.subTest(url=url):
                got_kind, owner, repo, got_ref = _classify(url)
                self.assertEqual((got_kind, got_ref), (kind, ref))
                self.assertTrue(owner and repo)

    def test_non_content_github_urls_fall_through_to_the_article_adapter(self):
        adapter = for_url("https://github.com/lightningnetwork/lnd")
        self.assertEqual(adapter.site, "article")


class GitHubParsingTests(unittest.TestCase):
    """Field mapping against the documented api.github.com response shapes."""

    def test_pull_request(self):
        url = "https://github.com/lightningnetwork/lnd/pull/9068"
        api = "https://api.github.com/repos/lightningnetwork/lnd/pulls/9068"
        payload = {
            "html_url": url,
            "title": "sweep: fix budget for first-stage HTLC sweeps",
            "user": {"login": "yyforyongyu"},
            "body": "This PR fixes the budget calculation.\n\nFixes #9000.",
            "state": "closed",
            "merged": True,
            "created_at": "2024-09-06T10:11:12Z",
            "merged_at": "2024-10-01T09:00:00Z",
            "base": {"ref": "master"},
            "changed_files": 12,
        }
        record = GitHubAdapter().parse(url, StubFetcher({api: json.dumps(payload)}))
        self.assertEqual(record.kind, "github-pr")
        self.assertEqual(record.title, "sweep: fix budget for first-stage HTLC sweeps")
        self.assertEqual(record.authors, ["yyforyongyu"])
        self.assertEqual(record.published, "2024-09-06")
        self.assertEqual(record.updated, "2024-10-01")
        self.assertEqual(record.extra["repo"], "lightningnetwork/lnd")
        self.assertTrue(record.extra["merged"])
        self.assertTrue(record.summary)

    def test_security_advisory(self):
        url = "https://github.com/lightningnetwork/lnd/security/advisories/GHSA-9gxx-58q6-42p7"
        api = (
            "https://api.github.com/repos/lightningnetwork/lnd"
            "/security-advisories/GHSA-9gxx-58q6-42p7"
        )
        payload = {
            "ghsa_id": "GHSA-9gxx-58q6-42p7",
            "cve_id": "CVE-2024-38359",
            "summary": "lnd's onion processing is vulnerable to a DoS",
            "description": "A parsing vulnerability in lnd's onion processing logic.",
            "severity": "high",
            "published_at": "2024-06-20T00:00:00Z",
            "updated_at": "2024-06-21T00:00:00Z",
            "cvss": {"score": 7.5, "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H"},
            "cwes": [{"cwe_id": "CWE-400"}],
            "publisher": {"login": "Roasbeef"},
            "references": ["https://morehouse.github.io/lightning/lnd-onion-bomb/"],
            "vulnerabilities": [
                {
                    "package": {"name": "github.com/lightningnetwork/lnd", "ecosystem": "go"},
                    "vulnerable_version_range": "< 0.17.0-beta",
                    "patched_versions": "0.17.0-beta",
                }
            ],
        }
        record = GitHubAdapter().parse(url, StubFetcher({api: json.dumps(payload)}))
        self.assertEqual(record.kind, "github-security-advisory")
        self.assertEqual(record.cves, ["CVE-2024-38359"])
        self.assertEqual(record.extra["severity"], "high")
        self.assertEqual(record.extra["cvss"], 7.5)
        self.assertEqual(record.extra["affected"][0]["patched"], "0.17.0-beta")
        self.assertEqual(record.published, "2024-06-20")

    def test_release(self):
        url = "https://github.com/lightningnetwork/lnd/releases/tag/v0.15.4-beta"
        api = "https://api.github.com/repos/lightningnetwork/lnd/releases/tags/v0.15.4-beta"
        payload = {
            "tag_name": "v0.15.4-beta",
            "name": "lnd v0.15.4-beta",
            "body": "This release fixes a block parsing bug.",
            "published_at": "2022-11-02T00:00:00Z",
            "author": {"login": "Roasbeef"},
            "prerelease": False,
        }
        record = GitHubAdapter().parse(url, StubFetcher({api: json.dumps(payload)}))
        self.assertEqual(record.kind, "github-release")
        self.assertEqual(record.extra["tag"], "v0.15.4-beta")
        self.assertEqual(record.published, "2022-11-02")


class ReadmeParsingTests(unittest.TestCase):
    def setUp(self):
        self.entries = discover.parse_readme(ROOT / "README.md")
        self.by_title = {e.title: e for e in self.entries}

    def test_every_advisory_section_is_found(self):
        self.assertGreaterEqual(len(self.entries), 20)
        self.assertIn("DoS: LND Onion Bomb", self.by_title)

    def test_entry_fields(self):
        entry = self.by_title["DoS: LND Onion Bomb"]
        self.assertEqual(entry.slug, "dos-lnd-onion-bomb")
        self.assertEqual(entry.disclosure, "June 18, 2024")
        self.assertEqual(entry.patched, "lnd 0.17.0-beta")
        self.assertEqual(entry.cves, ["CVE-2024-38359"])
        self.assertIn("https://morehouse.github.io/lightning/lnd-onion-bomb/", entry.references)
        self.assertTrue(entry.summary.startswith("A parsing vulnerability"))

    def test_slugs_match_the_index_anchors(self):
        # index.sh builds the table of contents from the same rule.
        self.assertEqual(discover.slugify("LND: gossip_timestamp_filter DoS"),
                         "lnd-gossip_timestamp_filter-dos")

    def test_known_urls_are_deduplicated(self):
        urls = discover.known_urls(self.entries)
        self.assertEqual(len(urls), len(set(urls)))

    def test_every_url_has_an_adapter(self):
        for url in discover.known_urls(self.entries):
            with self.subTest(url=url):
                self.assertIsNotNone(for_url(url))


class DiscoveryFingerprintTests(unittest.TestCase):
    def test_host_aliases_and_si_prefix_collapse(self):
        a = "https://lightning.community/SI/2024/06/20/lnd-onion-bomb.html"
        b = "https://security.lightning.engineering/2024/06/20/lnd-onion-bomb.html"
        self.assertEqual(discover._fingerprint(a), discover._fingerprint(b))

    def test_unpublished_advisory_is_reported_as_new(self):
        entries = [discover.Entry(title="x", slug="x", references=[
            "https://lightning.community/SI/2024/06/20/lnd-onion-bomb.html"])]
        covered = {discover._fingerprint(u) for u in discover.known_urls(entries)}
        other = "https://security.lightning.engineering/2026/08/11/lnd-update-fee-breach-exploit.html"
        self.assertNotIn(discover._fingerprint(other), covered)


class RenderTests(unittest.TestCase):
    def test_parse_date_formats(self):
        cases = {
            "2024-06-20": "2024-06-20",
            "June 18, 2024": "2024-06-18",
            "Jun 20, 2024": "2024-06-20",
            "Published June 20, 2024": "2024-06-20",
            "2024-06-18T17:48:35.623Z": "2024-06-18",
            "Fri, 27 Sep 2019 21:31:46 +0930": "2019-09-27",
            "not a date": None,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(render.parse_date(raw), expected)

    def test_find_cves_is_ordered_and_deduplicated(self):
        self.assertEqual(
            render.find_cves("CVE-2019-12999 and CVE-2019-12998", "CVE-2019-12999"),
            ["CVE-2019-12999", "CVE-2019-12998"],
        )

    def test_first_paragraph_skips_headings_and_greetings(self):
        body = "# Title\n\nHi,\n\n" + "A real paragraph that is long enough to be a summary."
        self.assertTrue(render.first_paragraph(body).startswith("A real paragraph"))

    def test_html_to_markdown_absolutises_relative_links(self):
        md = render.html_to_markdown(
            '<p>see <a href="/patch">this</a></p>', base_url="https://example.org/a/b.html"
        )
        self.assertIn("https://example.org/patch", md)

    def test_noise_elements_are_dropped(self):
        md = render.html_to_markdown("<div><script>bad()</script><p>keep</p><nav>x</nav></div>")
        self.assertEqual(md, "keep")


if __name__ == "__main__":
    unittest.main()
