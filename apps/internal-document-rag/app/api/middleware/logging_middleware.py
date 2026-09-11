from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOGGER = logging.getLogger("api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every incoming API request and execution duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        path = request.url.path
        method = request.method

        LOGGER.info("API Request Start: %s %s", method, path)

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000.0
            LOGGER.info(
                "API Request Completed: %s %s -> %s (%.2fms)",
                method,
                path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
            return response
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            LOGGER.error(
                "API Request Failed: %s %s (%.2fms) Exception: %s",
                method,
                path,
                duration_ms,
                exc,
                exc_info=True,
            )
            raise exc
