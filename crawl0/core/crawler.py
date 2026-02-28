"""Multi-page async BFS crawler."""

from __future__ import annotations

import asyncio
from collections import deque
from urllib.parse import urlparse

from crawl0.core.scraper import scrape_async
from crawl0.models import ScrapeResult
from crawl0.utils.robots import RobotsChecker


class Crawler:
    """BFS crawler that scrapes multiple pages from a starting URL.

    Args:
        max_depth: Maximum link depth from the starting URL.
        max_pages: Maximum number of pages to scrape.
        same_domain_only: Only follow links on the same domain.
        respect_robots: Respect robots.txt.
        force_playwright: Force Playwright for all pages.
        delay: Delay between requests in seconds.
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_pages: int = 50,
        same_domain_only: bool = True,
        respect_robots: bool = True,
        force_playwright: bool = False,
        delay: float = 1.0,
    ) -> None:
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        self.respect_robots = respect_robots
        self.force_playwright = force_playwright
        self.delay = delay

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def _same_domain(self, url: str, base_domain: str) -> bool:
        """Check if URL belongs to the same domain."""
        return urlparse(url).netloc == base_domain

    async def crawl(self, start_url: str) -> list[ScrapeResult]:
        """BFS crawl from start_url, returning scraped results.

        Args:
            start_url: The URL to start crawling from.

        Returns:
            List of ScrapeResult for each crawled page.
        """
        start_url = self._normalize_url(start_url)
        base_domain = urlparse(start_url).netloc
        robots = RobotsChecker() if self.respect_robots else None

        visited: set[str] = set()
        results: list[ScrapeResult] = []
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])

        while queue and len(results) < self.max_pages:
            url, depth = queue.popleft()
            normalized = self._normalize_url(url)

            if normalized in visited:
                continue
            visited.add(normalized)

            # Robots check
            if robots:
                allowed = await robots.is_allowed(normalized)
                if not allowed:
                    continue

            # Scrape
            result = await scrape_async(
                normalized,
                force_playwright=self.force_playwright,
                respect_robots=False,  # Already checked above
            )
            results.append(result)

            if len(results) >= self.max_pages:
                break

            # Extract and enqueue links if not at max depth
            if depth < self.max_depth and not result.error:
                for link in result.links:
                    link_normalized = self._normalize_url(link)
                    if link_normalized in visited:
                        continue
                    if self.same_domain_only and not self._same_domain(link, base_domain):
                        continue
                    # Skip non-http(s)
                    if not link_normalized.startswith(("http://", "https://")):
                        continue
                    # Skip common non-page extensions
                    path = urlparse(link_normalized).path.lower()
                    skip_exts = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip",
                                 ".mp3", ".mp4", ".css", ".js", ".xml", ".rss"}
                    if any(path.endswith(ext) for ext in skip_exts):
                        continue
                    queue.append((link_normalized, depth + 1))

        return results


async def crawl_async(
    url: str,
    max_depth: int = 3,
    max_pages: int = 50,
    same_domain_only: bool = True,
    respect_robots: bool = True,
    force_playwright: bool = False,
) -> list[ScrapeResult]:
    """Crawl a website starting from url.

    Args:
        url: Starting URL.
        max_depth: Maximum crawl depth.
        max_pages: Maximum pages to scrape.
        same_domain_only: Stay on the same domain.
        respect_robots: Respect robots.txt.
        force_playwright: Force JS rendering.

    Returns:
        List of ScrapeResult objects.
    """
    crawler = Crawler(
        max_depth=max_depth,
        max_pages=max_pages,
        same_domain_only=same_domain_only,
        respect_robots=respect_robots,
        force_playwright=force_playwright,
    )
    return await crawler.crawl(url)


def crawl(
    url: str,
    max_depth: int = 3,
    max_pages: int = 50,
    same_domain_only: bool = True,
    respect_robots: bool = True,
) -> list[ScrapeResult]:
    """Synchronous wrapper for crawl_async."""
    return asyncio.run(
        crawl_async(url, max_depth, max_pages, same_domain_only, respect_robots)
    )
