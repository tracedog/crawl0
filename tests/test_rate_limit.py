"""Tests for rate limiter."""

import asyncio
import time
from crawl0.utils.rate_limit import RateLimiter


def test_rate_limiter_delays():
    limiter = RateLimiter(default_delay=0.1)
    start = time.monotonic()

    async def run():
        await limiter.wait("https://example.com/page1")
        await limiter.wait("https://example.com/page2")

    asyncio.run(run())
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1  # second request should wait


def test_different_domains_no_delay():
    limiter = RateLimiter(default_delay=1.0)
    start = time.monotonic()

    async def run():
        await limiter.wait("https://example.com/page1")
        await limiter.wait("https://other.com/page1")

    asyncio.run(run())
    elapsed = time.monotonic() - start
    assert elapsed < 0.5  # different domains, no delay
