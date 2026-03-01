"""Core scraper — auto-detects static vs JS-rendered pages."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from playwright.async_api import async_playwright

from crawl0.core.parser import parse_html
from crawl0.core.stealth import (
    BrowserFingerprint,
    detect_captcha,
    detect_waf,
    gaussian_delay,
    generate_fingerprint,
    simulate_human_behavior,
)
from crawl0.models import ScrapeResult
from crawl0.utils.proxy import ProxyEntry, ProxyRotator
from crawl0.utils.rate_limit import RateLimiter
from crawl0.utils.robots import RobotsChecker

# Legacy defaults (used when stealth is off)
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
    "<!--",
    "__NEXT_DATA__",
    "__NUXT__",
    "window.__INITIAL_STATE__",
    "root",
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

    text = body.get_text(strip=True)
    if len(text) < 100:
        return True

    for indicator in JS_INDICATORS:
        if indicator in html:
            if len(text) < 200:
                return True

    return False


async def _scrape_httpx(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    follow_redirects: bool = True,
    proxy: ProxyEntry | None = None,
    fingerprint: BrowserFingerprint | None = None,
) -> tuple[str, int]:
    """Fast path: scrape with httpx (no JS rendering)."""
    if fingerprint:
        req_headers = dict(fingerprint.headers)
    else:
        req_headers = {**DEFAULT_HEADERS, "User-Agent": DEFAULT_USER_AGENT}
    if headers:
        req_headers.update(headers)

    proxy_url = proxy.server_url if proxy else None

    async with httpx.AsyncClient(
        headers=req_headers,
        timeout=timeout,
        follow_redirects=follow_redirects,
        verify=False,
        proxy=proxy_url,
    ) as client:
        response = await client.get(url)
        return response.text, response.status_code


async def _scrape_playwright(
    url: str,
    timeout: float = 30000,
    wait_for: str = "networkidle",
    fingerprint: BrowserFingerprint | None = None,
    stealth: bool = False,
    proxy: ProxyEntry | None = None,
) -> tuple[str, int]:
    """Full path: scrape with Playwright (JS rendering)."""
    fp = fingerprint or generate_fingerprint(full_stealth=False)

    launch_kwargs: dict[str, Any] = {"headless": True}
    if stealth:
        launch_kwargs["args"] = fp.playwright_launch_args
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy.server_url}

    async with async_playwright() as p:
        browser_type = p.firefox if fp.browser_type == "firefox" else p.chromium
        browser = await browser_type.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=fp.user_agent,
            viewport=fp.viewport,
            locale=fp.accept_language.split(",")[0],
            timezone_id=fp.timezone if stealth else None,
        )

        # Inject navigator overrides before any page loads
        if stealth:
            await context.add_init_script(fp.navigator_overrides_js)

        page = await context.new_page()

        # Set extra headers
        await page.set_extra_http_headers(
            {k: v for k, v in fp.headers.items() if k != "User-Agent"}
        )

        # Block unnecessary resources for speed
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )

        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        status_code = response.status if response else 0

        try:
            await page.wait_for_load_state(wait_for, timeout=10000)
        except Exception:
            pass

        # Human-like behavior
        if stealth:
            await simulate_human_behavior(page, full_stealth=True)

        html = await page.content()
        await browser.close()
        return html, status_code


async def screenshot_async(
    url: str,
    output_path: str = "screenshot.png",
    full_page: bool = True,
    stealth: bool = False,
    proxy: ProxyEntry | None = None,
) -> str:
    """Take a screenshot of a URL."""
    fp = generate_fingerprint(full_stealth=stealth)
    launch_kwargs: dict[str, Any] = {"headless": True}
    if stealth:
        launch_kwargs["args"] = fp.playwright_launch_args
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy.server_url}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=fp.user_agent,
            viewport=fp.viewport,
        )
        if stealth:
            await context.add_init_script(fp.navigator_overrides_js)
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        if stealth:
            await simulate_human_behavior(page, full_stealth=True)
        await page.screenshot(path=output_path, full_page=full_page)
        await browser.close()
    return output_path


async def scrape_async(
    url: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    stealth: bool = False,
    proxy: ProxyEntry | None = None,
    proxy_rotator: ProxyRotator | None = None,
) -> ScrapeResult:
    """Scrape a URL and return structured result.

    Args:
        url: URL to scrape.
        force_playwright: Skip auto-detection, always use Playwright.
        respect_robots: Check robots.txt before scraping.
        headers: Additional HTTP headers.
        timeout: Request timeout in seconds.
        stealth: Enable full stealth mode (fingerprint randomization, human behavior).
        proxy: Single proxy to use.
        proxy_rotator: ProxyRotator for automatic proxy rotation.

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

    # Generate fingerprint (always — basic stealth by default)
    fingerprint = generate_fingerprint(full_stealth=stealth)

    # Resolve proxy
    active_proxy = proxy
    if not active_proxy and proxy_rotator:
        active_proxy = proxy_rotator.get_next()

    method = "playwright" if force_playwright else "httpx"
    html = ""
    status_code = 0
    max_retries = 2 if stealth else 0

    for attempt in range(max_retries + 1):
        try:
            if not force_playwright:
                html, status_code = await _scrape_httpx(
                    url,
                    headers=headers,
                    timeout=timeout,
                    proxy=active_proxy,
                    fingerprint=fingerprint,
                )

                if _needs_js_rendering(html):
                    method = "playwright"
                    html, status_code = await _scrape_playwright(
                        url,
                        timeout=timeout * 1000,
                        fingerprint=fingerprint,
                        stealth=stealth,
                        proxy=active_proxy,
                    )
            else:
                html, status_code = await _scrape_playwright(
                    url,
                    timeout=timeout * 1000,
                    fingerprint=fingerprint,
                    stealth=stealth,
                    proxy=active_proxy,
                )

            # Report proxy success
            if active_proxy and proxy_rotator:
                proxy_rotator.report_success(active_proxy)

            # Check for WAF — retry with new fingerprint if stealth is on
            waf = detect_waf(html, status_code)
            if waf and stealth and attempt < max_retries:
                fingerprint = generate_fingerprint(full_stealth=True)
                if proxy_rotator:
                    active_proxy = proxy_rotator.get_next()
                await asyncio.sleep(gaussian_delay(2.0, 0.5, 1.0))
                continue

            # Parse
            markdown, metadata, links, images = parse_html(html, url)
            captcha = detect_captcha(html)

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
                captcha_detected=captcha,
                waf_detected=waf,
            )

        except Exception as e:
            # Report proxy failure
            if active_proxy and proxy_rotator:
                proxy_rotator.report_failure(active_proxy)
                active_proxy = proxy_rotator.get_next()

            if attempt < max_retries and stealth:
                fingerprint = generate_fingerprint(full_stealth=True)
                await asyncio.sleep(gaussian_delay(1.5, 0.5, 0.5))
                continue

            elapsed = (time.monotonic() - start) * 1000
            return ScrapeResult(
                url=url,
                status_code=status_code,
                html=html,
                error=str(e),
                elapsed_ms=elapsed,
                method=method,
            )

    # Should never reach here, but just in case
    elapsed = (time.monotonic() - start) * 1000
    return ScrapeResult(
        url=url,
        status_code=status_code,
        html=html,
        elapsed_ms=elapsed,
        method=method,
    )


def scrape(
    url: str,
    force_playwright: bool = False,
    respect_robots: bool = True,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    stealth: bool = False,
    proxy: ProxyEntry | None = None,
    proxy_rotator: ProxyRotator | None = None,
) -> ScrapeResult:
    """Synchronous wrapper for scrape_async."""
    return asyncio.run(
        scrape_async(
            url,
            force_playwright=force_playwright,
            respect_robots=respect_robots,
            headers=headers,
            timeout=timeout,
            stealth=stealth,
            proxy=proxy,
            proxy_rotator=proxy_rotator,
        )
    )
