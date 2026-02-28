<p align="center">
  <h1 align="center">🕷️ Crawl0</h1>
  <p align="center"><strong>The open-source Firecrawl alternative. Free forever.</strong></p>
  <p align="center">Scrape any website → get clean, LLM-ready markdown or structured JSON. No API keys. No usage limits. No vendor lock-in.</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/crawl0/"><img src="https://img.shields.io/pypi/v/crawl0?color=blue&label=PyPI" alt="PyPI version"></a>
  <a href="https://github.com/tracedog/crawl0/actions"><img src="https://img.shields.io/github/actions/workflow/status/tracedog/crawl0/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/tracedog/crawl0/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <img src="https://img.shields.io/pypi/pyversions/crawl0" alt="Python versions">
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#cli-reference">CLI</a> •
  <a href="#python-library">Python Library</a> •
  <a href="#api-server">API</a> •
  <a href="#plugin-system">Plugins</a> •
  <a href="#docker">Docker</a>
</p>

---

## Why Crawl0?

Firecrawl charges **$19–$399/mo** for something that should be a `pip install`.

Crawl0 gives you the same capabilities — and more — for free:

| | **Firecrawl** | **Crawl0** |
|---|:---:|:---:|
| **Price** | $19–$399/mo | **Free forever** |
| Self-hosted | ❌ SaaS only | ✅ Docker or pip |
| LLM-ready output | ✅ | ✅ Markdown, JSON, structured |
| JS rendering | ✅ | ✅ Playwright auto-detect |
| Site crawling | ✅ | ✅ BFS with depth control |
| Anti-bot bypass | Basic | ✅ Stealth mode, fingerprint rotation |
| Batch processing | Limited | ✅ Unlimited concurrency |
| API server | ✅ | ✅ FastAPI + Swagger docs |
| CLI | ❌ | ✅ Full-featured |
| Python library | ❌ | ✅ `from crawl0 import scrape` |
| Structured extraction | ✅ | ✅ Schema-based (Pydantic) |
| Screenshots | ✅ | ✅ |
| PDF generation | ❌ | ✅ |
| Sitemap discovery | ✅ | ✅ |
| Webhooks | ✅ | ✅ |
| Plugin system | ❌ | ✅ Custom extractors |
| Proxy rotation | ❌ | ✅ HTTP/HTTPS/SOCKS5 |
| Rate limiting | Their limits | **You control** |
| Data privacy | Their servers | **Your servers** |

---

## Quick Start

### Install

```bash
pip install crawl0
playwright install chromium
```

### Scrape in 3 Lines

```python
from crawl0 import scrape

result = scrape("https://example.com")
print(result.markdown)
```

### Or Use the CLI

```bash
crawl0 scrape https://example.com
```

That's it. Clean markdown output, ready for your LLM pipeline.

---

## Features

- 🚀 **Smart auto-detection** — tries fast `httpx` first, falls back to Playwright for JS-heavy pages
- 🧹 **Clean output** — strips nav, footer, ads, popups → pure content markdown
- 🕵️ **Stealth mode** — browser fingerprint randomization, human-like delays, proxy rotation
- 🔌 **Plugin system** — built-in extractors for restaurants, e-commerce, contacts, social profiles
- 📸 **Screenshots & PDFs** — full-page capture with one command
- 🗺️ **Site crawling** — BFS crawler with depth control, same-domain filtering
- ⚡ **Batch processing** — scrape hundreds of URLs concurrently
- 🌐 **API server** — self-hosted FastAPI with async job queue and webhooks
- 🤖 **robots.txt respect** — on by default, easily overridable

---

## CLI Reference

### `crawl0 scrape`

Scrape a single URL.

```bash
# Markdown output (default)
crawl0 scrape https://example.com

# JSON output
crawl0 scrape https://example.com -f json

# Save to file
crawl0 scrape https://example.com -o page.md

# Force Playwright (JS rendering)
crawl0 scrape https://example.com --playwright

# Stealth mode with proxy
crawl0 scrape https://example.com --stealth --proxy http://proxy:8080

# Ignore robots.txt
crawl0 scrape https://example.com --no-robots
```

### `crawl0 crawl`

Crawl an entire website.

```bash
# Crawl with depth 3 (default)
crawl0 crawl https://example.com

# Limit depth and pages
crawl0 crawl https://example.com --depth 2 --max-pages 20

# Save all pages to a directory
crawl0 crawl https://example.com -o ./output -f json

# Allow cross-domain links
crawl0 crawl https://example.com --all-domains
```

### `crawl0 extract`

Extract structured data using a schema.

```bash
# Extract restaurant data
crawl0 extract https://restaurant.com -s restaurant

# Extract product data
crawl0 extract https://shop.com/product -s ecommerce

# Extract contact info
crawl0 extract https://company.com/contact -s contact

# Extract social profile
crawl0 extract https://twitter.com/user -s social
```

### `crawl0 batch`

Process multiple URLs from a file.

```bash
# urls.txt: one URL per line
crawl0 batch urls.txt -o ./results -c 10
```

### `crawl0 screenshot`

Capture a screenshot.

```bash
crawl0 screenshot https://example.com -o screenshot.png
crawl0 screenshot https://example.com --viewport  # viewport only
```

### `crawl0 pdf`

Generate a PDF from a URL.

```bash
crawl0 pdf https://example.com -o output.pdf
```

### `crawl0 sitemap`

Discover all URLs from a sitemap.

```bash
crawl0 sitemap https://example.com
```

---

## Python Library

### Scrape a Page

```python
from crawl0 import scrape

result = scrape("https://example.com")

print(result.markdown)       # Clean markdown content
print(result.metadata.title) # Page title
print(result.links)          # All links found
print(result.images)         # All images found
print(result.status_code)    # HTTP status
print(result.elapsed_ms)     # Time taken in ms
print(result.method)         # "httpx" or "playwright"
```

### Async Scraping

```python
import asyncio
from crawl0 import scrape_async

async def main():
    result = await scrape_async("https://example.com", stealth=True)
    print(result.markdown)

asyncio.run(main())
```

### Crawl a Website

```python
from crawl0 import crawl

pages = crawl("https://example.com", max_depth=2, max_pages=20)
for page in pages:
    print(f"{page.url}: {len(page.markdown)} chars")
```

### Extract Structured Data

```python
from crawl0 import extract

# Returns a Pydantic model
data = extract("https://restaurant.com", schema="restaurant")
print(data.model_dump_json(indent=2))
```

### Batch Processing

```python
from crawl0 import process_batch
import asyncio

urls = ["https://example.com", "https://example.org"]
results = asyncio.run(process_batch(urls, concurrency=5))
for r in results:
    print(f"{r.url}: {r.status_code}")
```

### Parse HTML Directly

```python
from crawl0 import parse_html

html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
markdown, metadata, links, images = parse_html(html, "https://example.com")
print(markdown)  # "# Hello\n\nWorld"
```

---

## API Server

Start the self-hosted API:

```bash
# With pip
crawl0-api  # or: uvicorn crawl0.api.main:app --host 0.0.0.0 --port 9000

# With Docker
docker compose up -d
```

Interactive docs at `http://localhost:9000/docs`

### Endpoints

#### `GET /health`

```bash
curl http://localhost:9000/health
# {"status":"ok","version":"1.0.0","jobs_active":0}
```

#### `POST /scrape`

```bash
curl -X POST http://localhost:9000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "format": "markdown"}'
```

#### `POST /crawl`

```bash
curl -X POST http://localhost:9000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_depth": 2, "max_pages": 10}'
```

#### `POST /extract`

```bash
curl -X POST http://localhost:9000/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://restaurant.com", "schema": "restaurant"}'
```

#### `POST /batch`

Returns a job ID for async processing:

```bash
curl -X POST http://localhost:9000/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com", "https://example.org"], "webhook_url": "https://your-server.com/hook"}'
```

#### `GET /jobs/{job_id}`

```bash
curl http://localhost:9000/jobs/{job_id}
```

#### `POST /screenshot`

Returns a PNG image.

```bash
curl -X POST http://localhost:9000/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' -o screenshot.png
```

#### `POST /pdf`

Returns a PDF file.

```bash
curl -X POST http://localhost:9000/pdf \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' -o output.pdf
```

---

## Plugin System

Crawl0 ships with built-in extraction plugins and supports custom ones.

### Built-in Plugins

| Plugin | Schema Name | Extracts |
|---|---|---|
| Restaurant | `restaurant` | Menu items, hours, phone, address, cuisine |
| E-commerce | `ecommerce` | Product name, price, images, reviews, availability |
| Contact | `contact` | Emails, phones, addresses, social links |
| Social | `social` | Profile name, bio, follower count, posts |

### Custom Plugin

Create your own extractor:

```python
from pydantic import BaseModel
from bs4 import BeautifulSoup
from crawl0.plugins.base import BaseExtractor

class JobPosting(BaseModel):
    title: str = ""
    company: str = ""
    salary: str = ""
    location: str = ""

class JobExtractor(BaseExtractor):
    schema_name = "job"
    output_model = JobPosting

    def extract(self, soup: BeautifulSoup, url: str) -> JobPosting:
        # Your extraction logic here
        title = soup.find("h1")
        return JobPosting(
            title=title.get_text(strip=True) if title else "",
        )
```

Register it:

```python
from crawl0.plugins import EXTRACTOR_REGISTRY
EXTRACTOR_REGISTRY["job"] = JobExtractor
```

---

## Docker

### Quick Run

```bash
docker build -t crawl0 .
docker run --rm crawl0 scrape https://example.com
```

### API Server

```bash
docker compose up -d
# API available at http://localhost:9000
# Docs at http://localhost:9000/docs
```

### Dockerfile

The included `Dockerfile` packages Crawl0 with Chromium for Playwright support. The `docker-compose.yml` runs the API server.

---

## Architecture

```
crawl0/
├── crawl0/                     # Python package
│   ├── __init__.py             # Public API: scrape, crawl, extract, parse_html
│   ├── core/
│   │   ├── scraper.py          # Smart scraper (httpx → Playwright auto-detect)
│   │   ├── crawler.py          # BFS website crawler
│   │   ├── parser.py           # HTML → clean markdown
│   │   ├── extractor.py        # Structured data extraction
│   │   ├── stealth.py          # Fingerprint generation, anti-detection
│   │   └── batch.py            # Concurrent batch processing
│   ├── plugins/                # Extraction plugins
│   │   ├── base.py             # BaseExtractor ABC
│   │   ├── restaurant.py       # Menu, hours, contact
│   │   ├── ecommerce.py        # Products, prices, reviews
│   │   ├── contact.py          # Emails, phones, addresses
│   │   └── social.py           # Profiles, posts, followers
│   ├── output/
│   │   ├── json_out.py         # JSON serialization
│   │   └── pdf.py              # PDF generation
│   ├── utils/
│   │   ├── robots.py           # robots.txt parser
│   │   ├── sitemap.py          # Sitemap discovery
│   │   ├── rate_limit.py       # Per-domain rate limiting
│   │   └── proxy.py            # Proxy rotation (HTTP/SOCKS5)
│   ├── api/                    # FastAPI server
│   │   ├── main.py             # Routes and middleware
│   │   ├── models.py           # Request/response schemas
│   │   ├── webhooks.py         # Webhook callbacks
│   │   └── workers/queue.py    # Async job queue
│   └── cli/main.py             # Typer CLI
├── tests/                      # Test suite
├── Dockerfile                  # Container with Chromium
├── docker-compose.yml          # API server stack
└── pyproject.toml              # Package config
```

### How It Works

1. **Auto-detection**: Crawl0 first tries `httpx` (fast, ~100ms). If the page has JS frameworks or minimal body text, it automatically falls back to Playwright.
2. **HTML cleaning**: BeautifulSoup strips nav, footer, ads, scripts, popups → extracts the main content → converts to clean markdown via `markdownify`.
3. **Stealth mode**: Generates randomized browser fingerprints (User-Agent, viewport, timezone, WebGL, Canvas), injects navigator overrides, simulates human scroll/mouse behavior.
4. **Rate limiting**: Per-domain tracking with configurable delays. Respectful by default.

---

## Configuration

Crawl0 works with zero configuration. For advanced use:

| Environment Variable | Default | Description |
|---|---|---|
| `CRAWL0_DEFAULT_TIMEOUT` | `30` | Request timeout in seconds |
| `CRAWL0_RATE_LIMIT` | `1.0` | Seconds between same-domain requests |
| `CRAWL0_RESPECT_ROBOTS` | `true` | Respect robots.txt |
| `CRAWL0_API_PORT` | `9000` | API server port |

---

## Contributing

We welcome contributions! Here's how:

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e '.[dev]'`
4. Make your changes
5. Run tests: `pytest`
6. Lint: `ruff check .`
7. Submit a PR

### Development Setup

```bash
git clone https://github.com/tracedog/crawl0.git
cd crawl0
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
pytest
```

---

## License

MIT License — Copyright (c) 2026 [aka0 Labs](https://aka0.net)

Free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built by <a href="https://aka0.net">aka0 Labs</a></strong><br>
  <sub>If Crawl0 saves you time or money, ⭐ the repo and spread the word.</sub>
</p>
