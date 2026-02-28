"""Sitemap discovery and parsing."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SITEMAP_INDEX_TAG = f"{{{SITEMAP_NS['sm']}}}sitemapindex"


async def _fetch_text(url: str, timeout: float = 15.0) -> str | None:
    """Fetch URL content as text, return None on failure."""
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return None


async def discover_sitemap_url(base_url: str) -> list[str]:
    """Discover sitemap URLs from robots.txt or common paths.

    Args:
        base_url: The website base URL.

    Returns:
        List of discovered sitemap URLs.
    """
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    sitemaps: list[str] = []

    # Try robots.txt first
    robots_text = await _fetch_text(f"{origin}/robots.txt")
    if robots_text:
        for line in robots_text.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                sm_url = line.split(":", 1)[1].strip()
                if sm_url:
                    sitemaps.append(sm_url)

    # Fallback: common sitemap paths
    if not sitemaps:
        for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/"]:
            text = await _fetch_text(f"{origin}{path}")
            if text and "<urlset" in text or (text and "<sitemapindex" in text):
                sitemaps.append(f"{origin}{path}")
                break

    return sitemaps if sitemaps else [f"{origin}/sitemap.xml"]


def _parse_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """Parse a sitemap XML, returning (page_urls, sub_sitemap_urls).

    Args:
        xml_text: Raw XML string.

    Returns:
        Tuple of (page URLs, nested sitemap URLs).
    """
    pages: list[str] = []
    sub_sitemaps: list[str] = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return pages, sub_sitemaps

    # Detect namespace
    tag = root.tag
    ns = ""
    if "}" in tag:
        ns = tag.split("}")[0] + "}"

    # Check if it's a sitemap index
    if "sitemapindex" in tag:
        for sm in root.findall(f"{ns}sitemap"):
            loc = sm.find(f"{ns}loc")
            if loc is not None and loc.text:
                sub_sitemaps.append(loc.text.strip())
    else:
        for url_elem in root.findall(f"{ns}url"):
            loc = url_elem.find(f"{ns}loc")
            if loc is not None and loc.text:
                pages.append(loc.text.strip())

    return pages, sub_sitemaps


async def parse_sitemap(sitemap_url: str, max_sitemaps: int = 50) -> list[str]:
    """Recursively parse a sitemap and return all page URLs.

    Args:
        sitemap_url: URL of the sitemap.
        max_sitemaps: Max number of sub-sitemaps to follow.

    Returns:
        List of all page URLs found.
    """
    all_urls: list[str] = []
    visited: set[str] = set()
    queue = [sitemap_url]
    sitemaps_processed = 0

    while queue and sitemaps_processed < max_sitemaps:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        sitemaps_processed += 1

        text = await _fetch_text(url)
        if not text:
            continue

        pages, sub_sitemaps = _parse_sitemap_xml(text)
        all_urls.extend(pages)
        queue.extend(sub_sitemaps)

    return list(dict.fromkeys(all_urls))  # deduplicate


async def get_sitemap_urls(base_url: str) -> list[str]:
    """Discover and parse all sitemaps for a website.

    Args:
        base_url: The website URL.

    Returns:
        List of all page URLs from all sitemaps.
    """
    sitemap_urls = await discover_sitemap_url(base_url)
    all_pages: list[str] = []
    for sm_url in sitemap_urls:
        pages = await parse_sitemap(sm_url)
        all_pages.extend(pages)
    return list(dict.fromkeys(all_pages))


def get_sitemap_urls_sync(base_url: str) -> list[str]:
    """Synchronous wrapper for get_sitemap_urls."""
    return asyncio.run(get_sitemap_urls(base_url))
