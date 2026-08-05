from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.database import async_session_factory
from app.observability.metrics import READINESS_FAILURES
from app.redis_client import redis_client

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "unavailable"
        READINESS_FAILURES.labels("postgres").inc()
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
        READINESS_FAILURES.labels("redis").inc()
    ready = all(value == "ok" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "checks": checks}
