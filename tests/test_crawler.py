"""Tests for the multi-page crawler."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from crawl0.core.crawler import Crawler
from crawl0.models import ScrapeResult


def _make_result(url: str, links: list[str] | None = None) -> ScrapeResult:
    return ScrapeResult(
        url=url,
        status_code=200,
        html="<html><body>Hello</body></html>",
        markdown="Hello",
        links=links or [],
    )


class TestCrawler:
    def test_normalize_url(self):
        crawler = Crawler()
        assert crawler._normalize_url("https://example.com/page/") == "https://example.com/page"
        assert crawler._normalize_url("https://example.com") == "https://example.com/"
        assert crawler._normalize_url("https://example.com/page#section") == "https://example.com/page"
        assert crawler._normalize_url("https://example.com/page?q=1") == "https://example.com/page?q=1"

    def test_same_domain(self):
        crawler = Crawler()
        assert crawler._same_domain("https://example.com/page", "example.com") is True
        assert crawler._same_domain("https://other.com/page", "example.com") is False

    @pytest.mark.asyncio
    async def test_crawl_respects_max_pages(self):
        results_to_return = [
            _make_result("https://example.com/", links=[
                "https://example.com/a", "https://example.com/b", "https://example.com/c",
            ]),
            _make_result("https://example.com/a"),
            _make_result("https://example.com/b"),
        ]
        call_count = 0

        async def mock_scrape(url, **kwargs):
            nonlocal call_count
            idx = min(call_count, len(results_to_return) - 1)
            result = results_to_return[idx]
            result.url = url
            call_count += 1
            return result

        with patch("crawl0.core.crawler.scrape_async", side_effect=mock_scrape):
            with patch("crawl0.core.crawler.RobotsChecker") as mock_robots:
                mock_robots.return_value.is_allowed = AsyncMock(return_value=True)
                crawler = Crawler(max_pages=2, max_depth=1)
                results = await crawler.crawl("https://example.com/")
                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_crawl_respects_same_domain(self):
        async def mock_scrape(url, **kwargs):
            return _make_result(url, links=[
                "https://example.com/page1",
                "https://evil.com/steal",
            ])

        with patch("crawl0.core.crawler.scrape_async", side_effect=mock_scrape):
            with patch("crawl0.core.crawler.RobotsChecker") as mock_robots:
                mock_robots.return_value.is_allowed = AsyncMock(return_value=True)
                crawler = Crawler(max_pages=10, max_depth=1, same_domain_only=True)
                results = await crawler.crawl("https://example.com/")
                urls = {r.url for r in results}
                assert "https://evil.com/steal" not in urls

    @pytest.mark.asyncio
    async def test_crawl_skips_file_extensions(self):
        async def mock_scrape(url, **kwargs):
            return _make_result(url, links=[
                "https://example.com/doc.pdf",
                "https://example.com/image.jpg",
                "https://example.com/page",
            ])

        with patch("crawl0.core.crawler.scrape_async", side_effect=mock_scrape):
            with patch("crawl0.core.crawler.RobotsChecker") as mock_robots:
                mock_robots.return_value.is_allowed = AsyncMock(return_value=True)
                crawler = Crawler(max_pages=10, max_depth=1)
                results = await crawler.crawl("https://example.com/")
                urls = {r.url for r in results}
                assert "https://example.com/doc.pdf" not in urls
                assert "https://example.com/image.jpg" not in urls
