"""Adapter contract shared by every live data source.

Every adapter exposes an async ``fetch()`` that:
  1. Tries the real public API when the required configuration is present.
  2. On any failure (missing config, timeout, non-2xx, malformed payload)
     falls back to a typed demo provider and marks the result ``DEMO``/``STALE``.
  3. Never raises out to the caller - a broken feed must not break the page
     (principle 2.7). The caller only ever sees a normal ``AdapterResponse``.

This is what section 35 calls "source-specific ingestion adapters"; the
router layer never talks to an external API directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, TypeVar

import httpx

from app.schemas.enums import DataStatus

logger = logging.getLogger("earthpulse.adapters")

T = TypeVar("T")

DEFAULT_TIMEOUT = httpx.Timeout(6.0, connect=3.0)


@dataclass
class AdapterResponse(Generic[T]):
    source_name: str
    status: DataStatus
    items: list[T] = field(default_factory=list)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = None


async def safe_get_json(
    url: str,
    params: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict | list | None:
    """GET JSON with a short timeout, returning None on any failure instead
    of raising. Adapters decide what "None" means for their fallback."""
    try:
        request_headers = {"User-Agent": "EarthPulse/0.1"}
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=request_headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001 - deliberately broad, feed must degrade gracefully
        logger.warning("adapter fetch failed url=%s error=%s", url, exc)
        return None


async def safe_get_bytes(url: str, params: dict | None = None) -> bytes | None:
    """GET a binary or XML product without letting a source outage break a view."""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": "EarthPulse/0.1"})
            resp.raise_for_status()
            return resp.content
    except Exception as exc:  # noqa: BLE001 - adapters degrade to typed unavailable responses
        logger.warning("adapter fetch failed url=%s error=%s", url, exc)
        return None
