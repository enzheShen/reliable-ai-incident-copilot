from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api import api_router
from app.api.health import router as health_router
from app.config import get_settings
from app.database import engine
from app.frontend import mount_frontend
from app.logging import configure_logging
from app.observability.middleware import BodySizeLimitMiddleware, ObservabilityMiddleware
from app.redis_client import redis_client

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await redis_client.aclose()
    await engine.dispose()


def create_app(*, manage_resources: bool = True) -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan if manage_resources else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.validated_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID", "X-Cache"],
    )
    application.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_incident_body_bytes)
    application.add_middleware(ObservabilityMiddleware)
    application.include_router(api_router)
    application.include_router(health_router)

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    mount_frontend(
        application,
        settings.frontend_dist_dir,
        required=settings.app_env == "production",
    )
    return application


app = create_app()
