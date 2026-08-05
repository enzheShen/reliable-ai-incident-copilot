from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import incidents as incidents_api
from app.main import create_app
from app.models import ReliabilityEvent, Runbook
from app.providers import DeterministicMockProvider, ProviderError, deterministic_assessment
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.analysis import PROVIDER_CIRCUITS, AnalysisService
from app.services.embeddings import runbook_embedding

pytestmark = pytest.mark.integration


def payload(service_name: str = "reliability-api") -> dict[str, Any]:
    return {
        "service_name": service_name,
        "environment": "production",
        "started_at": "2026-08-05T10:30:00Z",
        "symptoms": "p95 latency is above 2400ms.",
        "logs": ["slow request duration=2480ms"],
        "metrics": {"p95_latency_ms": 2480.0},
        "recent_changes": ["release 1.2.0"],
    }


async def seed_runbook(session: AsyncSession) -> None:
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


async def deterministic_mock(
    self: DeterministicMockProvider,
    incident: IncidentCreate,
    runbooks: list[RunbookMatch],
    prompt: str,
) -> ProviderAssessment:
    del self, prompt
    return deterministic_assessment(incident, runbooks, fallback=False)


@pytest.mark.asyncio
async def test_success_and_unrecovered_500_are_counted(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await seed_runbook(db_session)
    monkeypatch.setattr(DeterministicMockProvider, "assess", deterministic_mock)
    original_analyse = AnalysisService.analyse

    async def fail_selected(
        self: AnalysisService, incident: IncidentCreate
    ) -> Any:
        if incident.service_name == "forced-server-failure":
            raise RuntimeError("synthetic unrecovered failure")
        return await original_analyse(self, incident)

    monkeypatch.setattr(AnalysisService, "analyse", fail_selected)
    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        success = await client.post("/api/v1/incidents/analyse", json=payload())
        failure = await client.post(
            "/api/v1/incidents/analyse", json=payload("forced-server-failure")
        )
        summary = await client.get("/api/v1/reliability/summary")
        events = await client.get(
            "/api/v1/reliability/events", params={"window_minutes": 60}
        )
    assert success.status_code == 200
    assert failure.status_code == 500
    assert summary.status_code == 200
    assert summary.json()["request_count"] == 2
    assert summary.json()["success_rate"] == 0.5
    failure_events = [item for item in events.json() if item["event_type"] == "analysis_failure"]
    assert failure_events[0]["details"] == {
        "error_type": "RuntimeError",
        "stage": "provider_analysis",
    }
    stored = list(
        (
            await db_session.execute(
                select(ReliabilityEvent).where(
                    ReliabilityEvent.event_type == "analysis_failure"
                )
            )
        ).scalars()
    )
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_429_and_422_are_excluded_from_valid_request_denominator(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await seed_runbook(db_session)
    monkeypatch.setattr(DeterministicMockProvider, "assess", deterministic_mock)
    previous_limit = incidents_api.settings.rate_limit_per_minute
    incidents_api.settings.rate_limit_per_minute = 1
    try:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            success = await client.post("/api/v1/incidents/analyse", json=payload())
            limited = await client.post(
                "/api/v1/incidents/analyse", json=payload("rate-limited-api")
            )
            invalid = await client.post(
                "/api/v1/incidents/analyse", json={**payload("invalid-api"), "symptoms": "x"}
            )
            summary = await client.get("/api/v1/reliability/summary")
        assert success.status_code == 200
        assert limited.status_code == 429
        assert invalid.status_code == 422
        assert summary.json()["request_count"] == 1
        assert summary.json()["success_rate"] == 1.0
    finally:
        incidents_api.settings.rate_limit_per_minute = previous_limit


@pytest.mark.asyncio
async def test_successful_fallback_remains_a_success(
    db_session: AsyncSession,
    integration_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(incidents_api, "redis_client", integration_redis)
    await seed_runbook(db_session)
    PROVIDER_CIRCUITS.clear()

    async def fail_provider(
        self: DeterministicMockProvider,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        del self, incident, runbooks, prompt
        raise ProviderError("synthetic invalid output", retryable=False)

    monkeypatch.setattr(DeterministicMockProvider, "assess", fail_provider)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/incidents/analyse", json=payload())
        summary = await client.get("/api/v1/reliability/summary")
    assert response.status_code == 200
    assert response.json()["fallback_used"] is True
    assert summary.json()["request_count"] == 1
    assert summary.json()["success_rate"] == 1.0
    assert summary.json()["fallback_count"] == 1
