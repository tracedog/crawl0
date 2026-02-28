"""Tests for Crawl0 API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from crawl0.api.main import app
from crawl0.api.workers.queue import job_queue
from crawl0.api.models import JobStatus
from crawl0.models import ScrapeResult, PageMetadata


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_scrape_result():
    return ScrapeResult(
        url="https://example.com",
        status_code=200,
        html="<html><body>Hello</body></html>",
        markdown="# Hello\n\nWorld",
        metadata=PageMetadata(title="Example", description="Test page"),
        links=["https://example.com/about"],
        images=["https://example.com/logo.png"],
        elapsed_ms=150.0,
        method="httpx",
    )


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestScrape:
    @patch("crawl0.api.main.scrape_async")
    def test_scrape_markdown(self, mock_scrape, client, mock_scrape_result):
        mock_scrape.return_value = mock_scrape_result
        resp = client.post("/scrape", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com"
        assert data["content"] == "# Hello\n\nWorld"
        assert data["status_code"] == 200
        assert data["method"] == "httpx"

    @patch("crawl0.api.main.scrape_async")
    def test_scrape_html(self, mock_scrape, client, mock_scrape_result):
        mock_scrape.return_value = mock_scrape_result
        resp = client.post("/scrape", json={"url": "https://example.com", "format": "html"})
        assert resp.status_code == 200
        assert "<html>" in resp.json()["content"]

    @patch("crawl0.api.main.scrape_async")
    def test_scrape_error(self, mock_scrape, client):
        mock_scrape.side_effect = RuntimeError("Connection failed")
        resp = client.post("/scrape", json={"url": "https://example.com"})
        assert resp.status_code == 500

    def test_scrape_invalid_body(self, client):
        resp = client.post("/scrape", json={})
        assert resp.status_code == 422


class TestCrawl:
    @patch("crawl0.api.main.crawl_async")
    def test_crawl(self, mock_crawl, client, mock_scrape_result):
        mock_crawl.return_value = [mock_scrape_result]
        resp = client.post("/crawl", json={"url": "https://example.com", "max_depth": 1, "max_pages": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pages"] == 1
        assert len(data["pages"]) == 1

    @patch("crawl0.api.main.crawl_async")
    def test_crawl_error(self, mock_crawl, client):
        mock_crawl.side_effect = RuntimeError("Crawl failed")
        resp = client.post("/crawl", json={"url": "https://example.com"})
        assert resp.status_code == 500


class TestExtract:
    @patch("crawl0.api.main.extract_async")
    def test_extract(self, mock_extract, client):
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"name": "Test Restaurant", "hours": {}}
        mock_extract.return_value = mock_model
        resp = client.post("/extract", json={"url": "https://example.com", "schema": "restaurant"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema"] == "restaurant"  # alias in response
        assert "data" in data

    @patch("crawl0.api.main.extract_async")
    def test_extract_invalid_schema(self, mock_extract, client):
        mock_extract.side_effect = ValueError("Unknown schema 'bogus'")
        resp = client.post("/extract", json={"url": "https://example.com", "schema": "bogus"})
        assert resp.status_code == 422


class TestBatch:
    def test_batch_creates_job(self, client):
        with patch("crawl0.api.main.job_queue") as mock_q:
            mock_job = MagicMock()
            mock_job.job_id = "test-123"
            mock_job.status = JobStatus.queued
            mock_q.create_job.return_value = mock_job
            mock_q.run_job = AsyncMock()

            resp = client.post("/batch", json={
                "urls": ["https://example.com", "https://example.org"],
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["job_id"] == "test-123"
            assert data["total_urls"] == 2

    def test_batch_empty_urls(self, client):
        resp = client.post("/batch", json={"urls": []})
        assert resp.status_code == 422


class TestJobStatus:
    def test_job_not_found(self, client):
        resp = client.get("/jobs/nonexistent")
        assert resp.status_code == 404

    def test_job_found(self, client):
        from crawl0.api.models import OutputFormat
        job = job_queue.create_job(urls=["https://example.com"], format=OutputFormat.markdown)
        resp = client.get(f"/jobs/{job.job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job.job_id
        assert data["status"] == "queued"


class TestScreenshot:
    @patch("crawl0.api.main.screenshot_async")
    def test_screenshot(self, mock_ss, client, tmp_path):
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfakedata")

        async def _mock_ss(url, output_path, full_page):
            import shutil
            shutil.copy(str(png_file), output_path)
            return output_path

        mock_ss.side_effect = _mock_ss
        resp = client.post("/screenshot", json={"url": "https://example.com"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"


class TestPdf:
    @patch("crawl0.api.main.scrape_async")
    @patch("crawl0.api.main.markdown_to_pdf")
    def test_pdf(self, mock_pdf, mock_scrape, client, mock_scrape_result, tmp_path):
        mock_scrape.return_value = mock_scrape_result
        pdf_file = tmp_path / "out.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        mock_pdf.return_value = str(pdf_file)

        resp = client.post("/pdf", json={"url": "https://example.com"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
