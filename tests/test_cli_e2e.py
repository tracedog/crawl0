"""End-to-end CLI tests using Typer's test runner."""

from typer.testing import CliRunner
from crawl0.cli.main import app

runner = CliRunner()


class TestCLIBasic:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "crawl0" in result.stdout
        assert "1.0.0" in result.stdout

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "scrape" in result.stdout
        assert "crawl" in result.stdout

    def test_scrape_help(self):
        result = runner.invoke(app, ["scrape", "--help"])
        assert result.exit_code == 0
        assert "URL" in result.stdout
        assert "--format" in result.stdout

    def test_crawl_help(self):
        result = runner.invoke(app, ["crawl", "--help"])
        assert result.exit_code == 0
        assert "--depth" in result.stdout

    def test_extract_help(self):
        result = runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0
        assert "--schema" in result.stdout

    def test_batch_help(self):
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--concurrency" in result.stdout

    def test_screenshot_help(self):
        result = runner.invoke(app, ["screenshot", "--help"])
        assert result.exit_code == 0

    def test_pdf_help(self):
        result = runner.invoke(app, ["pdf", "--help"])
        assert result.exit_code == 0

    def test_sitemap_help(self):
        result = runner.invoke(app, ["sitemap", "--help"])
        assert result.exit_code == 0
