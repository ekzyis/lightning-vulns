"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import discover
from .adapters import for_url, scrape
from .fetch import Fetcher, FetchError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_README = ROOT / "README.md"
DEFAULT_OUT = ROOT / "data" / "sources.json"
DEFAULT_CACHE = ROOT / ".cache"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrape.py",
        description="Scrape every source referenced by README.md into data/sources.json.",
    )
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--only", metavar="SUBSTRING",
                        help="scrape just the URLs containing this substring")
    parser.add_argument("--refresh", action="store_true",
                        help="ignore cached bodies and re-download everything")
    parser.add_argument("--offline", action="store_true",
                        help="use only what is already cached; never hit the network")
    parser.add_argument("--list", action="store_true",
                        help="print the sources and their adapters, then exit")
    parser.add_argument("--check-new", action="store_true",
                        help="also report advisories published upstream but missing from README")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    entries = discover.parse_readme(args.readme)
    urls = discover.known_urls(entries)
    if args.only:
        urls = [u for u in urls if args.only in u]

    if args.list:
        for url in urls:
            adapter = for_url(url)
            print(f"{getattr(adapter, 'site', '?'):<28} {url}")
        print(f"\n{len(urls)} sources across {len(entries)} advisories", file=sys.stderr)
        return 0

    fetcher = Fetcher(args.cache, offline=args.offline, refresh=args.refresh)

    # Which advisories cite which URL — recorded on each scraped source.
    citations: dict[str, list[str]] = {}
    for entry in entries:
        for url in entry.references:
            citations.setdefault(url, []).append(entry.slug)

    records = []
    failures = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}", file=sys.stderr)
        try:
            record = scrape(url, fetcher)
        except (FetchError, LookupError, ValueError) as exc:
            print(f"    !! {exc}", file=sys.stderr)
            failures.append({"url": url, "error": str(exc)})
            continue
        except Exception as exc:  # a parser bug should not lose the whole run
            print(f"    !! {type(exc).__name__}: {exc}", file=sys.stderr)
            failures.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
            continue

        data = record.to_dict()
        data["cited_by"] = citations.get(url, [])
        records.append(data)

    document = {
        "advisories": [vars(e) for e in entries],
        "sources": records,
        "failures": failures,
    }

    if args.check_new:
        new = discover.find_new(fetcher, entries)
        document["undocumented"] = new
        if new:
            print(f"\n{len(new)} advisories published upstream but not in README:", file=sys.stderr)
            for url in new:
                print(f"  {url}", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"\nwrote {args.out.relative_to(ROOT)}: "
        f"{len(records)} sources, {len(failures)} failed",
        file=sys.stderr,
    )
    return 1 if failures else 0
