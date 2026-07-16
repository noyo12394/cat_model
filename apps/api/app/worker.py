"""Minimal background worker.

Section 34 calls for a Cloud Run + Pub/Sub + Cloud Scheduler ingestion
pipeline in production. This module is the local-dev stand-in: it
periodically runs the same source-health check the API exposes at
GET /api/v1/sources/status and logs the result, so `docker-compose up`
demonstrates a real (if simple) background process rather than an empty
placeholder container. A production deployment replaces the `while True`
loop below with Cloud Scheduler triggering a Cloud Run Job or Pub/Sub
message, calling the same adapters.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.services.source_health import get_source_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("earthpulse.worker")

POLL_INTERVAL_SECONDS = 300


async def run_forever() -> None:
    settings = get_settings()
    while True:
        try:
            statuses = await get_source_health(settings)
            for s in statuses:
                logger.info("source=%s status=%s detail=%s", s.key, s.status, s.detail)
        except Exception:  # noqa: BLE001 - a single bad cycle must not kill the worker
            logger.exception("Worker cycle failed; will retry after the poll interval.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
