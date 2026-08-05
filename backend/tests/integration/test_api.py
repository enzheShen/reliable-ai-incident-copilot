from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.models import Incident, Runbook
from app.providers import DeterministicMockProvider, deterministic_assessment
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.embeddings import runbook_embedding

pytestmark = pytest.mark.integration


async def seed_latency_runbook(session: AsyncSession) -> None:
    session.add(
        Runbook(
            id=UUID("00000000-0000-4000-8000-000000000001"),
            slug="api-latency-spike",
            title="API latency spike",
            content="Inspect route latency. Check dependencies. Roll back a correlated release.",
            embedding=runbook_embedding(
                "API latency spike", ["api", "latency", "p95", "slow request"]
            ),
            version=1,
        )
    )
    await session.commit()


def payload() -> dict[str, Any]:
    return {
        "service_name": "integration-api",
        "environment": "production",
        "started_at": "2026-08-05T10:30:00Z",
        "symptoms": "p95 latency is above 2400ms.",
        "logs": ["slow request duration=2480ms"],
        "metrics": {"p95_latency_ms": 2480.0},
        "recent_changes": ["release 1.2.0"],
    }


@pytest.mark.asyncio
async def test_analyse_idempotency_history_and_readiness(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del integration_redis
    await seed_latency_runbook(db_session)

    async def mock_assess(
        self: DeterministicMockProvider,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        del self, prompt
        return deterministic_assessment(incident, runbooks, fallback=False)

    monkeypatch.setattr(DeterministicMockProvider, "assess", mock_assess)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/incidents/analyse",
            json=payload(),
            headers={"Idempotency-Key": "integration-key"},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["severity"] == "SEV2"
        assert body["provider_used"] == "deterministic-mock"
        assert body["runbook_references"][0]["title"] == "API latency spike"

        replay = await client.post(
            "/api/v1/incidents/analyse",
            json=payload(),
            headers={"Idempotency-Key": "integration-key"},
        )
        assert replay.status_code == 200
        assert replay.json()["incident_id"] == body["incident_id"]
        assert replay.headers["X-Idempotent-Replay"] == "true"

        history = await client.get(
            "/api/v1/incidents",
            params={"page": 1, "page_size": 1, "service": "integration-api", "severity": "SEV2"},
        )
        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert history.json()["items"][0]["status"] == "assessed"
        readiness = await client.get("/health/ready")
        assert readiness.status_code == 200
        assert readiness.json()["checks"] == {"postgres": "ok", "redis": "ok"}

    assert await db_session.scalar(select(func.count(Incident.id))) == 1
