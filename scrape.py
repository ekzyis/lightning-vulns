#!/usr/bin/env python3
#
# Scrape every source referenced from README.md into data/sources.json.

import sys

from scraper.cli import main

if __name__ == "__main__":
    sys.exit(main())
