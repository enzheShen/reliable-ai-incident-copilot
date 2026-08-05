from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.logging import bind_correlation_id, reset_correlation_id
from app.observability.metrics import HTTP_DURATION, HTTP_REQUESTS

logger = logging.getLogger("incident_copilot.http")
UUID_PATH = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,36}(?=/|$)")
CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def normalized_path(path: str) -> str:
    return UUID_PATH.sub("/{incident_id}", path)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, max_bytes: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        if request.method in {"POST", "PUT", "PATCH"} and not content_length:
            body = await request.body()
            if len(body) > self.max_bytes:
                return JSONResponse({"detail": "Request body too large"}, status_code=413)
        return await call_next(request)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("x-correlation-id", "")
        request_id = supplied if CORRELATION_PATTERN.fullmatch(supplied) else str(uuid4())
        token = bind_correlation_id(request_id)
        started = perf_counter()
        route = normalized_path(request.url.path)
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = request_id
            return response
        finally:
            duration = perf_counter() - started
            HTTP_REQUESTS.labels(request.method, route, str(status_code)).inc()
            HTTP_DURATION.labels(request.method, route).observe(duration)
            logger.info(
                "request_complete",
                extra={
                    "method": request.method,
                    "path": route,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            reset_correlation_id(token)
