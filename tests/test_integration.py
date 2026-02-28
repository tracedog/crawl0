"""Integration tests — actually scrape known pages."""

import pytest
from crawl0.core.scraper import scrape_async
from crawl0.core.parser import parse_html
from crawl0.core.crawler import crawl_async


@pytest.mark.integration
class TestLiveScrape:
    """Tests that hit real URLs. Mark with -m integration to run separately."""

    @pytest.mark.asyncio
    async def test_scrape_example_com(self):
        """Scrape example.com — the most stable page on the internet."""
        result = await scrape_async("https://example.com", respect_robots=False)
        assert result.status_code == 200
        assert result.error is None
        assert "Example Domain" in result.markdown
        assert result.method in ("httpx", "playwright")
        assert result.elapsed_ms > 0
        assert result.metadata.title == "Example Domain"

    @pytest.mark.asyncio
    async def test_scrape_example_com_playwright(self):
        """Force Playwright rendering on example.com."""
        result = await scrape_async(
            "https://example.com",
            force_playwright=True,
            respect_robots=False,
        )
        assert result.status_code == 200
        assert "Example Domain" in result.markdown
        assert result.method == "playwright"

    @pytest.mark.asyncio
    async def test_crawl_example_com(self):
        """Crawl example.com (single page, no outbound links)."""
        results = await crawl_async(
            "https://example.com",
            max_depth=1,
            max_pages=5,
            respect_robots=False,
        )
        assert len(results) >= 1
        assert results[0].status_code == 200
        assert "Example Domain" in results[0].markdown


class TestParserIntegration:
    """Test parser with real-ish HTML."""

    def test_parse_complex_html(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Page</title><meta name="description" content="A test page"></head>
        <body>
            <nav><a href="/home">Home</a><a href="/about">About</a></nav>
            <main>
                <h1>Main Content</h1>
                <p>This is the main content of the page.</p>
                <a href="https://example.com/link1">Link 1</a>
                <img src="https://example.com/image.jpg" alt="An image">
            </main>
            <footer>Copyright 2026</footer>
            <script>console.log('hidden');</script>
        </body>
        </html>
        """
        markdown, metadata, links, images = parse_html(html, "https://example.com")
        assert "Main Content" in markdown
        assert metadata.title == "Test Page"
        assert metadata.description == "A test page"
        assert any("link1" in link for link in links)
        assert any("image.jpg" in img for img in images)
        # nav/footer/script content should be stripped
        assert "console.log" not in markdown
