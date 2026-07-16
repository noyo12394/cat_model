"""Lightweight security middleware: security headers + in-memory rate limiting.

For the MVP this is a single-process token-bucket keyed by client IP, which is
sufficient for local/dev and demo deployments. Section 40 calls for API rate
limiting, secure headers and CSP; a production deployment behind Cloud Run
would typically move rate limiting to an API gateway (e.g. Apigee, Cloud
Armor) and keep this middleware as defense in depth.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client_key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            return Response(
                content='{"detail": "Rate limit exceeded. Try again shortly."}',
                status_code=429,
                media_type="application/json",
            )
        window.append(now)
        return await call_next(request)
