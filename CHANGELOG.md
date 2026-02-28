# Changelog

All notable changes to Crawl0 are documented here.

## [1.0.0] — 2026-02-28

### 🚀 Launch Release

**Phase 5 — Polish + Launch Prep**
- Professional README with full documentation
- Comprehensive test suite (92+ unit tests + integration tests)
- GitHub Actions CI (Python 3.11, 3.12, lint with ruff)
- PyPI package ready (`pip install crawl0`)
- Code cleanup, docstrings, `py.typed` marker
- CHANGELOG and LICENSE

**Phase 4 — Stealth + Anti-Bot**
- Browser fingerprint randomization (User-Agent, viewport, timezone, WebGL, Canvas)
- Human-like behavior simulation (scroll, mouse movement, Gaussian delays)
- CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare Turnstile)
- WAF detection (Cloudflare, AWS WAF, Akamai, Sucuri)
- Proxy rotation support (HTTP, HTTPS, SOCKS5)
- Auto-retry with new fingerprint on WAF detection

**Phase 3 — API Server**
- FastAPI server with `/scrape`, `/crawl`, `/extract`, `/batch`, `/screenshot`, `/pdf`
- Async job queue for batch processing
- Webhook callbacks on job completion
- Auto-generated Swagger/OpenAPI docs
- Docker Compose for self-hosted deployment

**Phase 2 — Crawling + Extraction**
- BFS website crawler with configurable depth and page limits
- Sitemap discovery and parsing (XML + namespace handling)
- Structured data extraction with Pydantic schemas
- Plugin system with built-in extractors: restaurant, e-commerce, contact, social
- Screenshot capture (full page + viewport)
- PDF generation from scraped content
- Batch URL processing with concurrency control

**Phase 1 — Core Engine (MVP)**
- Smart auto-detection: httpx (fast) → Playwright (JS rendering) fallback
- HTML → clean markdown conversion (strips nav, footer, ads, scripts)
- JSON structured output with metadata, links, images
- CLI: `crawl0 scrape <url>` with format, output, and stealth options
- Per-domain rate limiting
- robots.txt respect (on by default)
- PyPI package structure

---

_Built by [aka0 Labs](https://aka0.net)_
