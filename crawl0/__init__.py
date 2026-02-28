"""Crawl0 — The open-source Firecrawl alternative."""

__version__ = "0.1.0"

from crawl0.core.scraper import scrape, scrape_async
from crawl0.core.parser import parse_html

__all__ = ["scrape", "scrape_async", "parse_html", "__version__"]
