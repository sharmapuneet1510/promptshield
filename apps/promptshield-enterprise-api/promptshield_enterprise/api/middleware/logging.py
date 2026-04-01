"""
Structured request logging middleware.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs each request with structured fields.

    Adds a X-Request-ID header to all responses and binds the request ID
    to the structlog context for the duration of the request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Bind request context for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=str(request.client.host) if request.client else "unknown",
        )

        response: Response | None = None
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "request",
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_error",
                error=str(exc),
                duration_ms=round(duration_ms, 2),
            )
            raise
