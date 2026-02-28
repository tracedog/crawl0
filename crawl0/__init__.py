"""Crawl0 — The open-source Firecrawl alternative."""

__version__ = "0.2.0"

from crawl0.core.scraper import scrape, scrape_async
from crawl0.core.parser import parse_html
from crawl0.core.crawler import crawl, crawl_async
from crawl0.core.extractor import extract, extract_async
from crawl0.core.batch import process_batch

__all__ = [
    "scrape",
    "scrape_async",
    "parse_html",
    "crawl",
    "crawl_async",
    "extract",
    "extract_async",
    "process_batch",
    "__version__",
]
