"""Data models for Crawl0."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PageMetadata(BaseModel):
    """Metadata extracted from a web page."""

    title: str | None = None
    description: str | None = None
    author: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_url: str | None = None
    og_type: str | None = None
    canonical_url: str | None = None
    language: str | None = None
    favicon: str | None = None


class ScrapeResult(BaseModel):
    """Result of scraping a single URL."""

    url: str
    status_code: int
    html: str = ""
    markdown: str = ""
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    links: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    elapsed_ms: float = 0.0
    method: str = "httpx"  # "httpx" or "playwright"
    captcha_detected: bool = False
    waf_detected: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
