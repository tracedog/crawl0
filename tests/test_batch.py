"""Tests for batch processing."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from crawl0.core.batch import load_urls_from_file, process_batch
from crawl0.models import ScrapeResult


class TestLoadUrls:
    def test_load_urls(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("https://example.com\n")
            f.write("# comment\n")
            f.write("\n")
            f.write("https://example.org\n")
            f.flush()
            urls = load_urls_from_file(f.name)
        assert urls == ["https://example.com", "https://example.org"]

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_urls_from_file("/nonexistent/file.txt")

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# only comments\n\n")
            f.flush()
            urls = load_urls_from_file(f.name)
        assert urls == []


class TestProcessBatch:
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        async def mock_scrape(url, **kwargs):
            return ScrapeResult(url=url, status_code=200, markdown="content")

        with patch("crawl0.core.batch.scrape_async", side_effect=mock_scrape):
            results = await process_batch(
                ["https://a.com", "https://b.com", "https://c.com"],
                concurrency=2,
            )
            assert len(results) == 3
            urls = {r.url for r in results}
            assert "https://a.com" in urls
            assert "https://b.com" in urls
            assert "https://c.com" in urls

    @pytest.mark.asyncio
    async def test_batch_callback(self):
        async def mock_scrape(url, **kwargs):
            return ScrapeResult(url=url, status_code=200)

        callback_results = []

        with patch("crawl0.core.batch.scrape_async", side_effect=mock_scrape):
            await process_batch(
                ["https://a.com", "https://b.com"],
                on_result=lambda r: callback_results.append(r.url),
            )
            assert len(callback_results) == 2
