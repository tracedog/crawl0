# 🕷️ Crawl0

<!-- Badges -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **The open-source Firecrawl alternative. Scrape any website. Get LLM-ready output. Free.**

Firecrawl charges $19–$399/mo for what should be a `pip install`. We fixed that.

---

## Features

- 🚀 **Smart scraping** — auto-detects static vs JS-rendered pages (httpx fast path, Playwright fallback)
- 📝 **LLM-ready markdown** — strips nav, footer, ads, scripts → clean readable content
- 📊 **Structured JSON** — metadata, links, images, all in one response
- 📸 **Screenshots** — full-page or viewport captures
- 🤖 **robots.txt** — respects by default, override with a flag
- ⏱️ **Rate limiting** — configurable per-domain delays
- 🐳 **Docker ready** — one command to containerize
- 🔧 **CLI + Python library** — use from terminal or import in your code

## Quick Start

### Install

```bash
pip install .
playwright install chromium
```

### CLI

```bash
# Scrape to markdown (default)
crawl0 scrape https://example.com

# Scrape to JSON
crawl0 scrape https://example.com --format json

# Save to file
crawl0 scrape https://example.com --output page.md

# Force Playwright (JS rendering)
crawl0 scrape https://example.com --playwright

# Screenshot
crawl0 screenshot https://example.com --output shot.png

# Ignore robots.txt
crawl0 scrape https://example.com --no-robots
```

### Python Library

```python
from crawl0 import scrape

result = scrape("https://example.com")
print(result.markdown)       # Clean markdown
print(result.metadata.title) # Page title
print(result.links)          # All links
print(result.images)         # All images
print(result.elapsed_ms)     # Time taken
```

### Async

```python
import asyncio
from crawl0 import scrape_async

async def main():
    result = await scrape_async("https://example.com")
    print(result.markdown)

asyncio.run(main())
```

### Docker (CLI)

```bash
docker compose build
docker compose run crawl0 scrape https://example.com --format json
```

### API Server

Start the API server on port 9000:

```bash
docker compose up -d
# or without Docker:
uvicorn crawl0.api.main:app --host 0.0.0.0 --port 9000
```

Swagger docs at [http://localhost:9000/docs](http://localhost:9000/docs)

#### Scrape a URL

```bash
curl -X POST http://localhost:9000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "format": "markdown"}'
```

#### Crawl a site

```bash
curl -X POST http://localhost:9000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_depth": 2, "max_pages": 10}'
```

#### Extract structured data

```bash
curl -X POST http://localhost:9000/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "schema": "restaurant"}'
```

#### Batch process URLs

```bash
# Submit batch job
curl -X POST http://localhost:9000/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com", "https://example.org"], "webhook_url": "https://myapp.com/hook"}'

# Check job status
curl http://localhost:9000/jobs/{job_id}
```

#### Screenshot

```bash
curl -X POST http://localhost:9000/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' --output screenshot.png
```

#### PDF

```bash
curl -X POST http://localhost:9000/pdf \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' --output page.pdf
```

#### Health check

```bash
curl http://localhost:9000/health
```

## Output Format (JSON)

```json
{
  "url": "https://example.com",
  "status_code": 200,
  "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples...",
  "metadata": {
    "title": "Example Domain",
    "description": null,
    "og_title": null,
    "language": "en"
  },
  "links": ["https://www.iana.org/domains/example"],
  "images": [],
  "scraped_at": "2026-02-28T21:00:00Z",
  "elapsed_ms": 342.5,
  "method": "httpx"
}
```

## vs Firecrawl

| | Firecrawl | Crawl0 |
|---|---|---|
| **Price** | $19–$399/mo | Free forever |
| **Self-hosted** | ❌ | ✅ |
| **CLI** | ❌ | ✅ |
| **Python library** | ❌ | ✅ |
| **JS rendering** | ✅ | ✅ |
| **LLM-ready output** | ✅ | ✅ |
| **Your data stays yours** | ❌ | ✅ |

## License

MIT — do whatever you want with it.

---

Built by [aka0 Labs](https://aka0.net) 🧪
