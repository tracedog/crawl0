"""robots.txt parser and checker."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsChecker:
    """Check if a URL is allowed by robots.txt.

    Caches robots.txt per domain to avoid re-fetching.
    """

    def __init__(self, user_agent: str = "crawl0") -> None:
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def _robots_url(self, url: str) -> str:
        """Get robots.txt URL for a given page URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    async def _fetch_robots(self, url: str) -> RobotFileParser:
        """Fetch and parse robots.txt for a domain."""
        robots_url = self._robots_url(url)
        domain = urlparse(url).netloc

        if domain in self._cache:
            return self._cache[domain]

        parser = RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                else:
                    # No robots.txt or error — allow everything
                    parser.allow_all = True
        except Exception:
            # Can't fetch robots.txt — allow by default
            parser.allow_all = True

        self._cache[domain] = parser
        return parser

    async def is_allowed(self, url: str) -> bool:
        """Check if the URL is allowed by robots.txt.

        Args:
            url: The URL to check.

        Returns:
            True if scraping is allowed, False if blocked.
        """
        parser = await self._fetch_robots(url)
        return parser.can_fetch(self.user_agent, url)
