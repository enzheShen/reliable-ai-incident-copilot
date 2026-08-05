from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import incidents as incidents_api
from app.main import create_app
from app.models import IdempotencyKey, Incident, Runbook
from app.providers import DeterministicMockProvider, deterministic_assessment
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.embeddings import runbook_embedding

pytestmark = pytest.mark.integration


def payload(*, symptoms: str = "p95 latency is above 2400ms.") -> dict[str, Any]:
    return {
        "service_name": "idempotency-api",
        "environment": "production",
        "started_at": "2026-08-05T10:30:00Z",
        "symptoms": symptoms,
        "logs": ["slow request duration=2480ms"],
        "metrics": {"p95_latency_ms": 2480.0},
        "recent_changes": ["release 1.2.0"],
    }


async def prepare(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    session.add(
        Runbook(
            id=UUID("00000000-0000-4000-8000-000000000001"),
            slug="api-latency-spike",
            title="API latency spike",
            content="Inspect route latency. Roll back a correlated release.",
            embedding=runbook_embedding("API latency spike", ["latency", "p95", "slow request"]),
            version=1,
        )
    )
    await session.commit()

    async def mock_assess(
        self: DeterministicMockProvider,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        del self, prompt
        return deterministic_assessment(incident, runbooks, fallback=False)

    monkeypatch.setattr(DeterministicMockProvider, "assess", mock_assess)


@pytest.mark.asyncio
async def test_active_replay_payload_conflict_and_rate_limit_order(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await prepare(db_session, monkeypatch)
    previous_limit = incidents_api.settings.rate_limit_per_minute
    incidents_api.settings.rate_limit_per_minute = 1
    try:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/api/v1/incidents/analyse",
                json=payload(),
                headers={"Idempotency-Key": "active-key"},
            )
            replay = await client.post(
                "/api/v1/incidents/analyse",
                json=payload(),
                headers={"Idempotency-Key": "active-key"},
            )
            conflict = await client.post(
                "/api/v1/incidents/analyse",
                json=payload(symptoms="A different valid latency symptom."),
                headers={"Idempotency-Key": "active-key"},
            )
        assert first.status_code == 200
        assert replay.status_code == 200
        assert replay.headers["X-Idempotent-Replay"] == "true"
        assert replay.json()["incident_id"] == first.json()["incident_id"]
        assert conflict.status_code == 409
        assert await db_session.scalar(select(func.count(Incident.id))) == 1
    finally:
        incidents_api.settings.rate_limit_per_minute = previous_limit


@pytest.mark.asyncio
async def test_expired_idempotency_key_can_be_reused(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await prepare(db_session, monkeypatch)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/incidents/analyse",
            json=payload(),
            headers={"Idempotency-Key": "expired-key"},
        )
        assert first.status_code == 200
        await db_session.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == "expired-key")
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db_session.commit()
        second = await client.post(
            "/api/v1/incidents/analyse",
            json=payload(),
            headers={"Idempotency-Key": "expired-key"},
        )
    assert second.status_code == 200
    assert second.json()["incident_id"] != first.json()["incident_id"]
    assert "X-Idempotent-Replay" not in second.headers
    assert await db_session.scalar(select(func.count(Incident.id))) == 2


@pytest.mark.asyncio
async def test_concurrent_same_key_persists_only_one_incident(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await prepare(db_session, monkeypatch)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(
            *[
                client.post(
                    "/api/v1/incidents/analyse",
                    json=payload(),
                    headers={"Idempotency-Key": "concurrent-key"},
                )
                for _ in range(2)
            ]
        )
    assert all(response.status_code in {200, 409} for response in responses)
    successful_ids = {
        response.json()["incident_id"] for response in responses if response.status_code == 200
    }
    assert len(successful_ids) == 1
    assert await db_session.scalar(select(func.count(Incident.id))) == 1
