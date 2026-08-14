# scraper

Scrapes every source referenced from `README.md` into a single structured
dataset at `data/sources.json`.

The point is that `README.md` stays the hand-written index — the scraper never
writes to it. It reads the references out of it, pulls down what each one says,
and normalises the result so that a rendered site (or any other consumer) can be
generated from data instead of from prose.

## Usage

```sh
pip install -r requirements.txt

python3 scrape.py                 # scrape everything into data/sources.json
python3 scrape.py --list          # show each source and the adapter that handles it
python3 scrape.py --check-new     # also report advisories upstream has that README does not
python3 scrape.py --only delving  # scrape just the URLs matching a substring
python3 scrape.py --refresh       # ignore the cache and re-download
python3 scrape.py --offline       # rebuild from cache only, no network
```

Set `GITHUB_TOKEN` before a full run. Anonymous GitHub API access is capped at
60 requests/hour, and there are 16 GitHub references to resolve.

```sh
GITHUB_TOKEN=ghp_... python3 scrape.py
```

## Output

`data/sources.json` has three parts (four with `--check-new`):

| Key | What it holds |
| --- | --- |
| `advisories` | Each `## ...` section of README.md: title, slug, disclosure date, patched versions, CVEs, summary, references |
| `sources` | One normalised record per referenced URL |
| `failures` | URLs that could not be scraped, with the error |
| `undocumented` | Advisories published upstream that README.md does not reference yet |

Every source record carries the same fields regardless of where it came from:

```json
{
  "url": "https://lightning.community/SI/2024/06/20/lnd-onion-bomb.html",
  "site": "lightning-labs-advisories",
  "kind": "advisory",
  "title": "LND Onion Bomb",
  "canonical_url": "...",
  "authors": ["Lightning Labs"],
  "published": "2024-06-20",
  "updated": null,
  "summary": "A parsing vulnerability in lnd's onion processing logic ...",
  "body_markdown": "## Impact\n\n...",
  "cves": ["CVE-2024-38359"],
  "links": ["https://morehouse.github.io/lightning/lnd-onion-bomb/"],
  "extra": { "severity": "T3 · Low", "cvss": "7.5/10", "...": "site-specific" },
  "content_sha256": "...",
  "cited_by": ["dos-lnd-onion-bomb"]
}
```

`body_markdown` is Markdown for every source, so a renderer never has to care
which site a given passage came from. `cited_by` holds README slugs, which match
the anchors `index.sh` generates. `content_sha256` covers `body_markdown` only,
so a re-run that changes nothing produces no diff.

Anything a single site offers that does not generalise goes in `extra` —
CVSS scores and affected/patched version tables for Lightning Labs advisories,
merge state for pull requests, thread tags for Delving Bitcoin, and so on.

## Adapters

`scraper/adapters/` holds one module per source type. The first adapter whose
`matches()` accepts a URL wins, and `ArticleAdapter` matches everything, so it
stays last in the registry.

| Adapter | Covers | Fetches |
| --- | --- | --- |
| `lightning_community` | lightning.community/SI, security.lightning.engineering | HTML |
| `discourse` | delvingbitcoin.org | topic JSON (`/t/<id>.json`) |
| `github` | PRs, issues, security advisories, releases, commits | api.github.com |
| `mailing_list` | lists.linuxfoundation.org, diyhpl.us | raw RFC822 |
| `article` | morehouse.github.io, nishantbansal2003.github.io, fallback | HTML |

To support a new site, add a module with `site`, `matches()` and `parse()`, and
register it in `scraper/adapters/__init__.py` above `ArticleAdapter`.

## Caching

Every response is written to `.cache/` (gitignored). Later runs revalidate with
`If-None-Match` / `If-Modified-Since`, so unchanged pages cost a 304 rather than
a download. Requests to a single host are spaced one second apart.

## Tests

```sh
python3 -m unittest discover tests
```

They run entirely against `tests/fixtures/`, so they need no network.
