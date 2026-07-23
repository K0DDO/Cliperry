"""Request logging middleware."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("cliperry.request")

# High-frequency probes — log at DEBUG to keep production INFO clean
_QUIET_PATHS = frozenset({"/health", "/ready"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach request id, measure latency, and emit structured access logs."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "request_failed method=%s path=%s duration_ms=%.1f request_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                request_id,
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-Id"] = request_id

        log = logger.debug if request.url.path in _QUIET_PATHS else logger.info
        log(
            "method=%s path=%s status=%s duration_ms=%.1f request_id=%s device_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
            getattr(request.state, "device_id", None),
        )
        # Never log raw query string — may contain download tokens.
        return response
