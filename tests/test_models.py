"""Tests for data models."""

from crawl0.models import ScrapeResult, PageMetadata


def test_scrape_result_defaults():
    result = ScrapeResult(url="https://example.com", status_code=200)
    assert result.url == "https://example.com"
    assert result.markdown == ""
    assert result.method == "httpx"
    assert result.error is None
    assert isinstance(result.metadata, PageMetadata)


def test_scrape_result_to_dict():
    result = ScrapeResult(url="https://example.com", status_code=200, markdown="# Hello")
    d = result.to_dict()
    assert d["url"] == "https://example.com"
    assert d["markdown"] == "# Hello"
    assert "scraped_at" in d


def test_page_metadata_defaults():
    meta = PageMetadata()
    assert meta.title is None
    assert meta.og_image is None
