"""Batch URL processing with configurable concurrency."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from crawl0.core.scraper import scrape_async
from crawl0.models import ScrapeResult


async def process_batch(
    urls: list[str],
    concurrency: int = 5,
    force_playwright: bool = False,
    respect_robots: bool = True,
    on_result: Callable[[ScrapeResult], None] | None = None,
) -> list[ScrapeResult]:
    """Process a batch of URLs with configurable concurrency.

    Args:
        urls: List of URLs to scrape.
        concurrency: Maximum concurrent requests.
        force_playwright: Force Playwright for all pages.
        respect_robots: Respect robots.txt.
        on_result: Optional callback for each completed result.

    Returns:
        List of ScrapeResult objects (same order as input URLs).
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[ScrapeResult | None] = [None] * len(urls)

    async def _scrape_one(idx: int, url: str) -> None:
        async with semaphore:
            result = await scrape_async(
                url,
                force_playwright=force_playwright,
                respect_robots=respect_robots,
            )
            results[idx] = result
            if on_result:
                on_result(result)

    tasks = [_scrape_one(i, url) for i, url in enumerate(urls)]
    await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def load_urls_from_file(file_path: str) -> list[str]:
    """Load URLs from a text file, one per line.

    Args:
        file_path: Path to the URL list file.

    Returns:
        List of URLs (empty lines and comments skipped).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"URL file not found: {file_path}")

    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls
