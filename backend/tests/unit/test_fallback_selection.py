from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.config import Settings
from app.providers import Provider, ProviderError, RuleBasedFallbackProvider
from app.reliability import CircuitBreaker
from app.repositories import RunbookMatch, RunbookRepository
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.analysis import AnalysisService


class FailingProvider(Provider):
    name = "failing-primary"
    model = "test-v1"

    async def assess(
        self, incident: IncidentCreate, runbooks: list[RunbookMatch], prompt: str
    ) -> ProviderAssessment:
        raise ProviderError("invalid output", retryable=False)


class FakeRedis:
    async def get(self, name: str) -> str | None:
        return None

    async def set(self, name: str, value: str, *, ex: int) -> object:
        return True


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)


@pytest.mark.asyncio
async def test_provider_failure_selects_explicit_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    match = RunbookMatch(
        id=UUID("00000000-0000-4000-8000-000000000003"),
        slug="redis-outage",
        title="Redis outage",
        content="Check reachability. Restore service.",
        version=1,
        relevance=0.9,
    )

    async def search(_: RunbookRepository, query: str, limit: int = 3) -> list[RunbookMatch]:
        return [match]

    monkeypatch.setattr(RunbookRepository, "search", search)
    incident = IncidentCreate(
        service_name="cache-api",
        environment="production",
        started_at=datetime(2026, 8, 5, tzinfo=UTC),
        symptoms="Redis requests are failing.",
        logs=["redis connection refused"],
        metrics={"cache_error_rate": 0.8},
        recent_changes=[],
    )
    service = AnalysisService(
        FakeSession(),  # type: ignore[arg-type]
        FakeRedis(),  # type: ignore[arg-type]
        settings=Settings(_env_file=None),
        primary=FailingProvider(),
        fallback=RuleBasedFallbackProvider(),
        circuit_breaker=CircuitBreaker(5, 60),
    )
    outcome = await service.analyse(incident)
    assert outcome.fallback_used is True
    assert outcome.provider_used == "rule-based-fallback"
    assert outcome.assessment.requires_human_escalation is True
