"""Crawl0 CLI — scrape any website from the command line."""

from __future__ import annotations

import asyncio
import json
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


@app.command()
def crawl(
    url: str = typer.Argument(..., help="Starting URL to crawl"),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum crawl depth"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Maximum pages to crawl"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    same_domain: bool = typer.Option(True, "--same-domain/--all-domains", help="Stay on same domain"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Force Playwright rendering"),
) -> None:
    """Crawl a website starting from a URL (BFS)."""
    from crawl0.core.crawler import crawl_async
    from crawl0.output.json_out import to_json

    results = asyncio.run(
        crawl_async(
            url,
            max_depth=depth,
            max_pages=max_pages,
            same_domain_only=same_domain,
            respect_robots=not no_robots,
            force_playwright=playwright,
        )
    )

    if output:
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, result in enumerate(results):
            ext = "json" if format == "json" else "md"
            filename = f"page_{i:04d}.{ext}"
            content = to_json(result) if format == "json" else result.markdown
            (out_dir / filename).write_text(content, encoding="utf-8")
        typer.secho(f"Saved {len(results)} pages to {output}/", fg=typer.colors.GREEN)
    else:
        for result in results:
            if format == "json":
                typer.echo(to_json(result))
            else:
                typer.echo(f"\n{'='*60}")
                typer.echo(f"URL: {result.url}")
                typer.echo(f"{'='*60}\n")
                typer.echo(result.markdown)

    typer.secho(
        f"\n--- Crawled {len(results)} pages ---",
        fg=typer.colors.BRIGHT_BLACK,
        err=True,
    )


@app.command()
def sitemap(
    url: str = typer.Argument(..., help="Website URL to discover sitemap"),
) -> None:
    """Discover and list all URLs from a website's sitemap."""
    from crawl0.utils.sitemap import get_sitemap_urls

    urls = asyncio.run(get_sitemap_urls(url))

    if not urls:
        typer.secho("No sitemap URLs found.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    for u in urls:
        typer.echo(u)

    typer.secho(
        f"\n--- {len(urls)} URLs found ---",
        fg=typer.colors.BRIGHT_BLACK,
        err=True,
    )


@app.command()
def extract(
    url: str = typer.Argument(..., help="URL to extract data from"),
    schema: str = typer.Option(..., "--schema", "-s", help="Extraction schema: restaurant, ecommerce, contact, social"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON output to file"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Force Playwright rendering"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
) -> None:
    """Extract structured data from a URL using a schema."""
    from crawl0.core.extractor import extract_async

    try:
        data = asyncio.run(
            extract_async(
                url,
                schema=schema,
                force_playwright=playwright,
                respect_robots=not no_robots,
            )
        )
    except (ValueError, RuntimeError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    content = data.model_dump_json(indent=2)

    if output:
        Path(output).write_text(content, encoding="utf-8")
        typer.secho(f"Saved to {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(content)


@app.command()
def batch(
    file: str = typer.Argument(..., help="Path to file with URLs (one per line)"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md, json"),
    output: str = typer.Option("./results", "--output", "-o", help="Output directory"),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Max concurrent requests"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Force Playwright rendering"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
) -> None:
    """Process a batch of URLs from a file."""
    from crawl0.core.batch import load_urls_from_file, process_batch
    from crawl0.output.json_out import to_json

    try:
        urls = load_urls_from_file(file)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if not urls:
        typer.secho("No URLs found in file.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    typer.secho(f"Processing {len(urls)} URLs (concurrency={concurrency})...", fg=typer.colors.BLUE)

    completed = 0

    def on_result(result):
        nonlocal completed
        completed += 1
        status = "✓" if not result.error else "✗"
        typer.secho(
            f"  [{completed}/{len(urls)}] {status} {result.url} ({result.elapsed_ms:.0f}ms)",
            fg=typer.colors.GREEN if not result.error else typer.colors.RED,
            err=True,
        )

    results = asyncio.run(
        process_batch(
            urls,
            concurrency=concurrency,
            force_playwright=playwright,
            respect_robots=not no_robots,
            on_result=on_result,
        )
    )

    # Save results
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, result in enumerate(results):
        ext = "json" if format == "json" else "md"
        filename = f"page_{i:04d}.{ext}"
        content = to_json(result) if format == "json" else result.markdown
        (out_dir / filename).write_text(content, encoding="utf-8")

    typer.secho(
        f"\n--- Processed {len(results)} URLs, saved to {output}/ ---",
        fg=typer.colors.GREEN,
    )


@app.command()
def pdf(
    url: str = typer.Argument(..., help="URL to convert to PDF"),
    output: str = typer.Option("output.pdf", "--output", "-o", help="Output PDF file path"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Force Playwright rendering"),
) -> None:
    """Scrape a URL and generate a PDF."""
    from crawl0.core.scraper import scrape_async
    from crawl0.output.pdf import markdown_to_pdf

    result = asyncio.run(scrape_async(url, force_playwright=playwright))

    if result.error:
        typer.secho(f"Error: {result.error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    path = markdown_to_pdf(
        result.markdown,
        output_path=output,
        title=result.metadata.title or result.url,
    )
    typer.secho(f"PDF saved to {path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
