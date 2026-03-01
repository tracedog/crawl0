"""End-to-end CLI tests using Typer's test runner."""

import re

from typer.testing import CliRunner

from crawl0.cli.main import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestCLIBasic:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        out = strip_ansi(result.stdout)
        assert "crawl0" in out
        assert "1.0.0" in out

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        out = strip_ansi(result.stdout)
        assert "scrape" in out
        assert "crawl" in out

    def test_scrape_help(self):
        result = runner.invoke(app, ["scrape", "--help"])
        assert result.exit_code == 0
        out = strip_ansi(result.stdout)
        assert "URL" in out or "url" in out
        assert "--format" in out

    def test_crawl_help(self):
        result = runner.invoke(app, ["crawl", "--help"])
        assert result.exit_code == 0
        assert "--depth" in strip_ansi(result.stdout)

    def test_extract_help(self):
        result = runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0
        assert "--schema" in strip_ansi(result.stdout)

    def test_batch_help(self):
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--concurrency" in strip_ansi(result.stdout)

    def test_screenshot_help(self):
        result = runner.invoke(app, ["screenshot", "--help"])
        assert result.exit_code == 0

    def test_pdf_help(self):
        result = runner.invoke(app, ["pdf", "--help"])
        assert result.exit_code == 0

    def test_sitemap_help(self):
        result = runner.invoke(app, ["sitemap", "--help"])
        assert result.exit_code == 0
