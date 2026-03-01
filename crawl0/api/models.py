"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class OutputFormat(str, Enum):
    markdown = "markdown"
    md = "md"
    json = "json"
    html = "html"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


# --- Scrape ---


class ScrapeRequest(BaseModel):
    url: str
    format: OutputFormat = OutputFormat.markdown
    force_playwright: bool = False
    respect_robots: bool = True
    timeout: float = 30.0
    stealth: bool = False
    proxy: str | None = None


class ScrapeResponse(BaseModel):
    url: str
    status_code: int
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0
    method: str = "httpx"
    captcha_detected: bool = False
    waf_detected: str | None = None
    error: str | None = None


# --- Crawl ---


class CrawlRequest(BaseModel):
    url: str
    max_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=50, ge=1, le=500)
    format: OutputFormat = OutputFormat.markdown
    same_domain_only: bool = True
    respect_robots: bool = True
    force_playwright: bool = False


class CrawlResponse(BaseModel):
    pages: list[ScrapeResponse]
    total_pages: int
    elapsed_ms: float


# --- Extract ---


class ExtractRequest(BaseModel):
    model_config = {"populate_by_name": True}
    url: str
    schema_name: str = Field(..., alias="schema")  # restaurant, ecommerce, contact, social
    force_playwright: bool = False
    respect_robots: bool = True


class ExtractResponse(BaseModel):
    model_config = {"populate_by_name": True}
    url: str
    schema_name: str = Field(..., alias="schema")
    data: dict[str, Any]
    elapsed_ms: float
    error: str | None = None


# --- Batch ---


class BatchRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=1000)
    format: OutputFormat = OutputFormat.markdown
    concurrency: int = Field(default=5, ge=1, le=50)
    force_playwright: bool = False
    respect_robots: bool = True
    webhook_url: str | None = None


class BatchResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    total_urls: int
    message: str = "Job queued"


# --- Screenshot ---


class ScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True


# --- PDF ---


class PdfRequest(BaseModel):
    url: str
    force_playwright: bool = False


# --- Job Status ---


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_urls: int = 0
    completed_urls: int = 0
    results: list[ScrapeResponse] | None = None
    error: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


# --- Health ---


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    jobs_active: int = 0
