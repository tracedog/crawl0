"""Configurable rate limiting for scraping."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse


class RateLimiter:
    """Per-domain rate limiter with configurable delay.

    Args:
        default_delay: Default delay between requests to the same domain (seconds).
        per_domain: Optional dict of domain-specific delays.
    """

    def __init__(
        self,
        default_delay: float = 1.0,
        per_domain: dict[str, float] | None = None,
    ) -> None:
        self.default_delay = default_delay
        self.per_domain = per_domain or {}
        self._last_request: dict[str, float] = {}

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    def _get_delay(self, domain: str) -> float:
        """Get the delay for a specific domain."""
        return self.per_domain.get(domain, self.default_delay)

    async def wait(self, url: str) -> None:
        """Wait if needed to respect rate limits for the given URL's domain."""
        domain = self._get_domain(url)
        delay = self._get_delay(domain)
        now = time.monotonic()
        last = self._last_request.get(domain, 0)
        elapsed = now - last

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request[domain] = time.monotonic()
