"""Structured data extraction using plugins."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from crawl0.core.scraper import scrape_async
from crawl0.plugins import EXTRACTORS


async def extract_async(
    url: str,
    schema: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
) -> BaseModel:
    """Scrape a URL and extract structured data using the specified schema.

    Args:
        url: URL to scrape and extract from.
        schema: Extraction schema name (restaurant, ecommerce, contact, social).
        force_playwright: Force Playwright rendering.
        respect_robots: Respect robots.txt.

    Returns:
        Pydantic model with extracted data.

    Raises:
        ValueError: If schema name is not recognized.
    """
    if schema not in EXTRACTORS:
        raise ValueError(
            f"Unknown schema '{schema}'. Available: {', '.join(EXTRACTORS.keys())}"
        )

    result = await scrape_async(
        url,
        force_playwright=force_playwright,
        respect_robots=respect_robots,
    )

    if result.error:
        raise RuntimeError(f"Scrape failed: {result.error}")

    extractor = EXTRACTORS[schema]()
    return extractor.extract_from_html(result.html, url)


def extract(
    url: str,
    schema: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
) -> BaseModel:
    """Synchronous wrapper for extract_async."""
    return asyncio.run(
        extract_async(url, schema, force_playwright, respect_robots)
    )
