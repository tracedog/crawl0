"""Webhook callback support for batch jobs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from crawl0.api.workers.queue import Job

logger = logging.getLogger("crawl0.api.webhooks")


async def send_webhook(job: Job) -> None:
    """POST job results to the configured webhook URL.

    Fire-and-forget: logs errors but never raises.
    """
    if not job.webhook_url:
        return

    payload = {
        "job_id": job.job_id,
        "status": job.status.value,
        "total_urls": len(job.urls),
        "completed_urls": job.completed_count,
        "results": [r.model_dump() for r in job.results],
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(job.webhook_url, json=payload)
            logger.info(f"Webhook sent to {job.webhook_url} — status {resp.status_code}")
    except Exception as e:
        logger.error(f"Webhook failed for job {job.job_id}: {e}")
