"""Crawl0 CLI — scrape any website from the command line."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

from crawl0 import __version__

app = typer.Typer(
    name="crawl0",
    help="The open-source Firecrawl alternative. Scrape any website. Get LLM-ready output.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"crawl0 {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Crawl0 — scrape any website, get clean markdown or JSON."""


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md, json, html"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save output to file"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Force Playwright rendering"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
    include_html: bool = typer.Option(False, "--include-html", help="Include raw HTML in JSON output"),
) -> None:
    """Scrape a URL and output clean markdown, JSON, or HTML."""
    from crawl0.core.scraper import scrape_async
    from crawl0.output.json_out import to_json

    result = asyncio.run(
        scrape_async(
            url,
            force_playwright=playwright,
            respect_robots=not no_robots,
        )
    )

    if result.error:
        typer.secho(f"Error: {result.error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Format output
    if format == "json":
        content = to_json(result, include_html=include_html)
    elif format == "html":
        content = result.html
    else:
        content = result.markdown

    # Output
    if output:
        Path(output).write_text(content, encoding="utf-8")
        typer.secho(f"Saved to {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(content)

    # Stats to stderr
    typer.secho(
        f"\n--- {result.method} | {result.status_code} | {result.elapsed_ms:.0f}ms | "
        f"{len(result.links)} links | {len(result.images)} images ---",
        fg=typer.colors.BRIGHT_BLACK,
        err=True,
    )


@app.command()
def screenshot(
    url: str = typer.Argument(..., help="URL to screenshot"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
    full_page: bool = typer.Option(True, "--full-page/--viewport", help="Full page or viewport only"),
) -> None:
    """Take a screenshot of a URL."""
    from crawl0.core.scraper import screenshot_async

    path = asyncio.run(screenshot_async(url, output_path=output, full_page=full_page))
    typer.secho(f"Screenshot saved to {path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
