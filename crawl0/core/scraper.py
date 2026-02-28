"""Core scraper — auto-detects static vs JS-rendered pages."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from playwright.async_api import async_playwright

from crawl0.core.parser import parse_html
from crawl0.models import ScrapeResult
from crawl0.utils.rate_limit import RateLimiter
from crawl0.utils.robots import RobotsChecker

# Stealth defaults
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# Indicators that a page needs JS rendering
JS_INDICATORS = [
    "<!--",  # common in SSR hydration
    "__NEXT_DATA__",
    "__NUXT__",
    "window.__INITIAL_STATE__",
    "root",  # React root with no content
    '<div id="app"></div>',
    '<div id="root"></div>',
    "noscript",
]

_rate_limiter = RateLimiter()


def _needs_js_rendering(html: str) -> bool:
    """Heuristic: does this page need JavaScript to render content?"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    body = soup.body
    if not body:
        return True

    # If body has very little visible text, likely JS-rendered
    text = body.get_text(strip=True)
    if len(text) < 100:
        return True

    # Check for SPA framework markers with empty content
    for indicator in JS_INDICATORS:
        if indicator in html:
            # Check if there's actual content alongside the indicator
            if len(text) < 200:
                return True

    return False


async def _scrape_httpx(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    follow_redirects: bool = True,
) -> tuple[str, int]:
    """Fast path: scrape with httpx (no JS rendering)."""
    req_headers = {**DEFAULT_HEADERS, "User-Agent": DEFAULT_USER_AGENT}
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient(
        headers=req_headers,
        timeout=timeout,
        follow_redirects=follow_redirects,
        verify=False,
    ) as client:
        response = await client.get(url)
        return response.text, response.status_code


async def _scrape_playwright(
    url: str,
    timeout: float = 30000,
    wait_for: str = "networkidle",
) -> tuple[str, int]:
    """Full path: scrape with Playwright (JS rendering)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport=DEFAULT_VIEWPORT,
            locale="en-US",
        )
        page = await context.new_page()

        # Block unnecessary resources for speed
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )

        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        status_code = response.status if response else 0

        # Wait for content to render
        try:
            await page.wait_for_load_state(wait_for, timeout=10000)
        except Exception:
            pass  # networkidle timeout is acceptable

        html = await page.content()
        await browser.close()
        return html, status_code


async def screenshot_async(
    url: str,
    output_path: str = "screenshot.png",
    full_page: bool = True,
) -> str:
    """Take a screenshot of a URL.

    Args:
        url: URL to screenshot.
        output_path: File path for the screenshot.
        full_page: Capture full page or just viewport.

    Returns:
        Path to the saved screenshot.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport=DEFAULT_VIEWPORT,
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.screenshot(path=output_path, full_page=full_page)
        await browser.close()
    return output_path


async def scrape_async(
    url: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> ScrapeResult:
    """Scrape a URL and return structured result.

    Auto-detects whether to use httpx (fast, static) or Playwright (JS rendering).

    Args:
        url: URL to scrape.
        force_playwright: Skip auto-detection, always use Playwright.
        respect_robots: Check robots.txt before scraping.
        headers: Additional HTTP headers.
        timeout: Request timeout in seconds.

    Returns:
        ScrapeResult with markdown, html, metadata, links, images.
    """
    start = time.monotonic()

    # Check robots.txt
    if respect_robots:
        checker = RobotsChecker()
        allowed = await checker.is_allowed(url)
        if not allowed:
            return ScrapeResult(
                url=url,
                status_code=0,
                error="Blocked by robots.txt. Use respect_robots=False to override.",
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

    # Rate limit
    await _rate_limiter.wait(url)

    method = "playwright" if force_playwright else "httpx"
    html = ""
    status_code = 0

    try:
        if not force_playwright:
            # Try httpx first (fast path)
            html, status_code = await _scrape_httpx(url, headers=headers, timeout=timeout)

            # Check if we need JS rendering
            if _needs_js_rendering(html):
                method = "playwright"
                html, status_code = await _scrape_playwright(url, timeout=timeout * 1000)
        else:
            html, status_code = await _scrape_playwright(url, timeout=timeout * 1000)

        # Parse
        markdown, metadata, links, images = parse_html(html, url)

        elapsed = (time.monotonic() - start) * 1000
        return ScrapeResult(
            url=url,
            status_code=status_code,
            html=html,
            markdown=markdown,
            metadata=metadata,
            links=links,
            images=images,
            elapsed_ms=elapsed,
            method=method,
        )

    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return ScrapeResult(
            url=url,
            status_code=status_code,
            html=html,
            error=str(e),
            elapsed_ms=elapsed,
            method=method,
        )


def scrape(
    url: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> ScrapeResult:
    """Synchronous wrapper for scrape_async.

    Args:
        url: URL to scrape.
        force_playwright: Skip auto-detection, always use Playwright.
        respect_robots: Check robots.txt before scraping.
        headers: Additional HTTP headers.
        timeout: Request timeout in seconds.

    Returns:
        ScrapeResult with markdown, html, metadata, links, images.
    """
    return asyncio.run(
        scrape_async(
            url,
            force_playwright=force_playwright,
            respect_robots=respect_robots,
            headers=headers,
            timeout=timeout,
        )
    )
