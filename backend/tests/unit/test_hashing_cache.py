from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.reliability import AssessmentCache, assessment_cache_key, request_hash
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment


def make_incident(metrics: dict[str, float] | None = None) -> IncidentCreate:
    return IncidentCreate(
        service_name="api",
        environment="staging",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        symptoms="Latency is above the normal threshold.",
        logs=["slow request"],
        metrics=metrics or {"p95": 2000.0, "errors": 0.1},
        recent_changes=[],
    )


def make_runbook(version: int = 1) -> RunbookMatch:
    return RunbookMatch(
        id=UUID("00000000-0000-4000-8000-000000000001"),
        slug="api-latency-spike",
        title="API latency spike",
        content="Check latency.",
        version=version,
        relevance=0.8,
    )


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, name: str) -> str | None:
        return self.values.get(name)

    async def set(self, name: str, value: str, *, ex: int) -> object:
        assert ex == 900
        self.values[name] = value
        return True


def test_request_hash_is_canonical_and_changes_with_payload() -> None:
    first = make_incident({"p95": 2000.0, "errors": 0.1})
    reordered = make_incident({"errors": 0.1, "p95": 2000.0})
    changed = make_incident({"errors": 0.2, "p95": 2000.0})
    assert request_hash(first) == request_hash(reordered)
    assert request_hash(first) != request_hash(changed)


def test_cache_key_includes_runbook_version_and_provider() -> None:
    incident = make_incident()
    original = assessment_cache_key(incident, [make_runbook(1)], "mock", "v1")
    assert original != assessment_cache_key(incident, [make_runbook(2)], "mock", "v1")
    assert original != assessment_cache_key(incident, [make_runbook(1)], "anthropic", "v1")


@pytest.mark.asyncio
async def test_assessment_cache_round_trip() -> None:
    client = FakeRedis()
    cache = AssessmentCache(client, 900)
    assessment = ProviderAssessment(
        severity="SEV3",
        summary="Latency is elevated but the service remains available.",
        likely_causes=["Traffic increase"],
        evidence=["p95=2000"],
        recommended_actions=["Inspect route latency"],
        confidence=0.7,
        requires_human_escalation=False,
    )
    assert await cache.get("key") is None
    await cache.set("key", assessment)
    assert await cache.get("key") == assessment
