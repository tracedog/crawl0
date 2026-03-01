"""In-memory async job queue for batch processing."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from crawl0.api.models import JobStatus, ScrapeResponse, OutputFormat


class Job:
    """Represents a batch processing job."""

    def __init__(
        self,
        urls: list[str],
        format: OutputFormat,
        concurrency: int,
        force_playwright: bool,
        respect_robots: bool,
        webhook_url: str | None = None,
    ):
        self.job_id: str = str(uuid.uuid4())
        self.urls = urls
        self.format = format
        self.concurrency = concurrency
        self.force_playwright = force_playwright
        self.respect_robots = respect_robots
        self.webhook_url = webhook_url
        self.status: JobStatus = JobStatus.queued
        self.results: list[ScrapeResponse] = []
        self.completed_count: int = 0
        self.error: str | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None


class JobQueue:
    """In-memory async job queue. Suitable for MVP / single-process deployment."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create_job(
        self,
        urls: list[str],
        format: OutputFormat = OutputFormat.markdown,
        concurrency: int = 5,
        force_playwright: bool = False,
        respect_robots: bool = True,
        webhook_url: str | None = None,
    ) -> Job:
        job = Job(urls, format, concurrency, force_playwright, respect_robots, webhook_url)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    @property
    def active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.status in (JobStatus.queued, JobStatus.running)
        )

    async def run_job(self, job: Job) -> None:
        """Execute a batch job asynchronously."""
        from crawl0.core.scraper import scrape_async
        from crawl0.api.webhooks import send_webhook

        job.status = JobStatus.running

        try:
            semaphore = asyncio.Semaphore(job.concurrency)
            results: list[ScrapeResponse | None] = [None] * len(job.urls)

            async def _scrape_one(idx: int, url: str) -> None:
                async with semaphore:
                    result = await scrape_async(
                        url,
                        force_playwright=job.force_playwright,
                        respect_robots=job.respect_robots,
                    )
                    fmt = job.format
                    if fmt in (OutputFormat.markdown, OutputFormat.md):
                        content = result.markdown
                    elif fmt == OutputFormat.html:
                        content = result.html
                    else:
                        content = result.to_dict().__repr__()

                    results[idx] = ScrapeResponse(
                        url=result.url,
                        status_code=result.status_code,
                        content=content,
                        metadata=result.metadata.model_dump(),
                        links=result.links,
                        images=result.images,
                        elapsed_ms=result.elapsed_ms,
                        method=result.method,
                        error=result.error,
                    )
                    job.completed_count += 1

            tasks = [_scrape_one(i, url) for i, url in enumerate(job.urls)]
            await asyncio.gather(*tasks)

            job.results = [r for r in results if r is not None]
            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            job.status = JobStatus.failed
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)

        # Fire webhook if configured
        if job.webhook_url:
            await send_webhook(job)


# Singleton
job_queue = JobQueue()
