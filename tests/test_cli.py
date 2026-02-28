"""Tests for CLI."""

from typer.testing import CliRunner
from crawl0.cli.main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "crawl0" in result.output


def test_scrape_missing_url():
    result = runner.invoke(app, ["scrape"])
    assert result.exit_code != 0
