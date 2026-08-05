from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Runbook
from app.reliability import AssessmentCache, RateLimiter, RateLimitExceeded
from app.reliability.cache import RedisCacheClient
from app.reliability.rate_limit import RedisRateLimitClient
from app.repositories import RunbookRepository
from app.schemas import ProviderAssessment
from app.services.embeddings import runbook_embedding

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_alembic_migration_created_pgvector_tables(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    assert result.scalar_one() == "vector"
    tables = await db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    assert {"incidents", "assessments", "runbooks", "idempotency_keys"} <= set(tables.scalars())


@pytest.mark.asyncio
async def test_pgvector_repository_returns_relevant_runbook(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            Runbook(
                id=UUID("00000000-0000-4000-8000-000000000001"),
                slug="api-latency-spike",
                title="API latency spike",
                content="Inspect latency.",
                embedding=runbook_embedding("API latency spike", ["latency", "p95"]),
                version=1,
            ),
            Runbook(
                id=UUID("00000000-0000-4000-8000-000000000003"),
                slug="redis-outage",
                title="Redis outage",
                content="Inspect Redis.",
                embedding=runbook_embedding(
                    "Redis outage", ["redis", "connection refused", "cache"]
                ),
                version=1,
            ),
        ]
    )
    await db_session.commit()
    matches = await RunbookRepository(db_session).search("redis cache connection refused", 1)
    assert matches[0].slug == "redis-outage"
    assert matches[0].relevance > 0.5


@pytest.mark.asyncio
async def test_real_redis_cache_and_rate_limiter(integration_redis: Redis) -> None:
    cache = AssessmentCache(cast(RedisCacheClient, integration_redis), 900)
    assessment = ProviderAssessment(
        severity="SEV3",
        summary="A validated synthetic assessment.",
        likely_causes=["Synthetic cause"],
        evidence=["synthetic evidence"],
        recommended_actions=["Inspect the synthetic service"],
        confidence=0.7,
        requires_human_escalation=False,
    )
    await cache.set("integration-key", assessment)
    assert await cache.get("integration-key") == assessment

    limiter = RateLimiter(cast(RedisRateLimitClient, integration_redis), 2)
    now = datetime(2026, 8, 5, tzinfo=UTC)
    await limiter.check("integration-client", now)
    await limiter.check("integration-client", now)
    with pytest.raises(RateLimitExceeded):
        await limiter.check("integration-client", now)
