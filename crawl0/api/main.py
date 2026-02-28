"""Crawl0 API Server — FastAPI application."""

from __future__ import annotations

import asyncio
import io
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

import crawl0
from crawl0.api.models import (
    BatchRequest,
    BatchResponse,
    CrawlRequest,
    CrawlResponse,
    ExtractRequest,
    ExtractResponse,
    HealthResponse,
    JobStatus,
    JobStatusResponse,
    OutputFormat,
    PdfRequest,
    ScrapeRequest,
    ScrapeResponse,
    ScreenshotRequest,
)
from crawl0.api.workers.queue import job_queue
from crawl0.core.scraper import scrape_async, screenshot_async
from crawl0.core.crawler import crawl_async
from crawl0.core.extractor import extract_async
from crawl0.output.pdf import markdown_to_pdf
from crawl0.utils.proxy import _parse_proxy

app = FastAPI(
    title="Crawl0 API",
    description="The open-source Firecrawl alternative. Scrape any website. Get LLM-ready output. Free.",
    version=crawl0.__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_content(result, fmt: OutputFormat) -> str:
    if fmt in (OutputFormat.markdown, OutputFormat.md):
        return result.markdown
    elif fmt == OutputFormat.html:
        return result.html
    else:  # json — return markdown (JSON structure is the response itself)
        return result.markdown


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=crawl0.__version__,
        jobs_active=job_queue.active_count,
    )


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest) -> ScrapeResponse:
    proxy_entry = _parse_proxy(req.proxy) if req.proxy else None
    try:
        result = await scrape_async(
            req.url,
            force_playwright=req.force_playwright,
            respect_robots=req.respect_robots,
            timeout=req.timeout,
            stealth=req.stealth,
            proxy=proxy_entry,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ScrapeResponse(
        url=result.url,
        status_code=result.status_code,
        content=_format_content(result, req.format),
        metadata=result.metadata.model_dump(),
        links=result.links,
        images=result.images,
        elapsed_ms=result.elapsed_ms,
        method=result.method,
        captcha_detected=result.captcha_detected,
        waf_detected=result.waf_detected,
        error=result.error,
    )


@app.post("/crawl", response_model=CrawlResponse)
async def crawl(req: CrawlRequest) -> CrawlResponse:
    start = time.monotonic()
    try:
        results = await crawl_async(
            req.url,
            max_depth=req.max_depth,
            max_pages=req.max_pages,
            same_domain_only=req.same_domain_only,
            respect_robots=req.respect_robots,
            force_playwright=req.force_playwright,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    pages = [
        ScrapeResponse(
            url=r.url,
            status_code=r.status_code,
            content=_format_content(r, req.format),
            metadata=r.metadata.model_dump(),
            links=r.links,
            images=r.images,
            elapsed_ms=r.elapsed_ms,
            method=r.method,
            error=r.error,
        )
        for r in results
    ]
    elapsed = (time.monotonic() - start) * 1000
    return CrawlResponse(pages=pages, total_pages=len(pages), elapsed_ms=elapsed)


@app.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest) -> ExtractResponse:
    start = time.monotonic()
    try:
        data = await extract_async(
            req.url,
            schema=req.schema_name,
            force_playwright=req.force_playwright,
            respect_robots=req.respect_robots,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = (time.monotonic() - start) * 1000
    return ExtractResponse(
        url=req.url,
        schema_name=req.schema_name,
        data=data.model_dump(),
        elapsed_ms=elapsed,
    )


@app.post("/batch", response_model=BatchResponse)
async def batch(req: BatchRequest) -> BatchResponse:
    job = job_queue.create_job(
        urls=req.urls,
        format=req.format,
        concurrency=req.concurrency,
        force_playwright=req.force_playwright,
        respect_robots=req.respect_robots,
        webhook_url=req.webhook_url,
    )
    # Fire and forget
    asyncio.create_task(job_queue.run_job(job))

    return BatchResponse(
        job_id=job.job_id,
        status=JobStatus.queued,
        total_urls=len(req.urls),
        message="Job queued for processing",
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total_urls=len(job.urls),
        completed_urls=job.completed_count,
        results=job.results if job.status == JobStatus.completed else None,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@app.post("/screenshot")
async def screenshot(req: ScreenshotRequest) -> Response:
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        await screenshot_async(req.url, output_path=tmp_path, full_page=req.full_page)
        data = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        return Response(content=data, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pdf")
async def pdf(req: PdfRequest) -> Response:
    try:
        result = await scrape_async(
            req.url,
            force_playwright=req.force_playwright,
        )
        if result.error:
            raise HTTPException(status_code=500, detail=result.error)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        output = markdown_to_pdf(
            result.markdown,
            output_path=tmp_path,
            title=result.metadata.title or req.url,
        )
        data = Path(output).read_bytes()
        media_type = "application/pdf" if output.endswith(".pdf") else "text/html"
        Path(output).unlink(missing_ok=True)
        return Response(content=data, media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
