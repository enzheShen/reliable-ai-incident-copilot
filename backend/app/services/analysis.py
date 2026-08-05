from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import ReliabilityEvent
from app.observability.metrics import (
    CACHE_HITS,
    CACHE_MISSES,
    CIRCUIT_BREAKER_STATE,
    LLM_DURATION,
    LLM_FAILURES,
    LLM_FALLBACK,
    LLM_REQUESTS,
)
from app.providers import (
    AnthropicProvider,
    DeterministicMockProvider,
    Provider,
    ProviderError,
    RuleBasedFallbackProvider,
    build_prompt,
)
from app.reliability import (
    AssessmentCache,
    CircuitBreaker,
    CircuitOpenError,
    assessment_cache_key,
    call_provider_with_retry,
)
from app.reliability.cache import RedisCacheClient
from app.repositories import RunbookMatch, RunbookRepository
from app.schemas import IncidentCreate, ProviderAssessment


@dataclass(frozen=True)
class AnalysisOutcome:
    assessment: ProviderAssessment
    runbooks: list[RunbookMatch]
    provider_used: str
    fallback_used: bool
    cache_hit: bool
    processing_time_ms: int


PROVIDER_CIRCUITS: dict[str, CircuitBreaker] = {}


def configured_primary_provider(settings: Settings) -> Provider:
    if settings.llm_mode == "live" and settings.anthropic_api_key:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return DeterministicMockProvider(settings.mock_llm_url, settings.llm_timeout_seconds)


class AnalysisService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        *,
        settings: Settings | None = None,
        primary: Provider | None = None,
        fallback: Provider | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings or get_settings()
        self.primary = primary or configured_primary_provider(self.settings)
        self.fallback = fallback or RuleBasedFallbackProvider()
        circuit_key = f"{self.primary.name}:{self.primary.model}"
        self.circuit_breaker = circuit_breaker or PROVIDER_CIRCUITS.setdefault(
            circuit_key,
            CircuitBreaker(
                self.settings.circuit_breaker_failure_threshold,
                self.settings.circuit_breaker_recovery_seconds,
            ),
        )
        self.cache = AssessmentCache(cast(RedisCacheClient, redis), self.settings.cache_ttl_seconds)
        CIRCUIT_BREAKER_STATE.labels(self.primary.name).set(
            {"closed": 0.0, "half_open": 0.5, "open": 1.0}[self.circuit_breaker.state.value]
        )

    async def _record_event(
        self, event_type: str, provider: str | None, details: dict[str, Any]
    ) -> None:
        self.session.add(
            ReliabilityEvent(event_type=event_type, provider=provider, details=details)
        )

    async def _record_transition(self, previous: object) -> None:
        current = self.circuit_breaker.state
        if previous != current:
            CIRCUIT_BREAKER_STATE.labels(self.primary.name).set(
                {"closed": 0.0, "half_open": 0.5, "open": 1.0}[current.value]
            )
            await self._record_event(
                "circuit_breaker_transition",
                self.primary.name,
                {"from": str(previous), "to": str(current)},
            )

    @staticmethod
    def retrieval_query(incident: IncidentCreate) -> str:
        return " ".join(
            [
                incident.service_name,
                incident.symptoms,
                *incident.logs,
                *incident.metrics.keys(),
                *incident.recent_changes,
            ]
        )

    async def analyse(self, incident: IncidentCreate) -> AnalysisOutcome:
        started = perf_counter()
        runbooks = await RunbookRepository(self.session).search(
            self.retrieval_query(incident), limit=3
        )
        prompt = build_prompt(incident, runbooks)
        key = assessment_cache_key(incident, runbooks, self.primary.name, self.primary.model)
        try:
            cached = await self.cache.get(key)
        except Exception as exc:
            cached = None
            await self._record_event(
                "cache_error", self.primary.name, {"error_type": type(exc).__name__}
            )
        if cached is not None:
            CACHE_HITS.labels(self.primary.name).inc()
            await self._record_event("cache_hit", self.primary.name, {})
            return AnalysisOutcome(
                assessment=cached,
                runbooks=runbooks,
                provider_used=self.primary.name,
                fallback_used=False,
                cache_hit=True,
                processing_time_ms=int((perf_counter() - started) * 1000),
            )
        CACHE_MISSES.labels(self.primary.name).inc()
        await self._record_event("cache_miss", self.primary.name, {})

        fallback_used = False
        provider_used = self.primary.name
        llm_started = perf_counter()
        try:
            previous_state = self.circuit_breaker.state
            await self.circuit_breaker.before_call()
            await self._record_transition(previous_state)
            result = await call_provider_with_retry(
                lambda: self.primary.assess(incident, runbooks, prompt),
                self.settings.llm_timeout_seconds,
            )
            LLM_REQUESTS.labels(self.primary.name, self.primary.model, "success").inc()
            LLM_DURATION.labels(self.primary.name, self.primary.model).observe(
                perf_counter() - llm_started
            )
            previous_state = self.circuit_breaker.state
            await self.circuit_breaker.record_success()
            await self._record_transition(previous_state)
            try:
                await self.cache.set(key, result)
            except Exception as exc:
                await self._record_event(
                    "cache_error", self.primary.name, {"error_type": type(exc).__name__}
                )
        except (ProviderError, CircuitOpenError) as exc:
            LLM_REQUESTS.labels(self.primary.name, self.primary.model, "failure").inc()
            LLM_DURATION.labels(self.primary.name, self.primary.model).observe(
                perf_counter() - llm_started
            )
            LLM_FAILURES.labels(self.primary.name, type(exc).__name__).inc()
            if isinstance(exc, ProviderError):
                previous_state = self.circuit_breaker.state
                await self.circuit_breaker.record_failure()
                await self._record_transition(previous_state)
            await self._record_event(
                "provider_failure",
                self.primary.name,
                {"error_type": type(exc).__name__, "retryable": getattr(exc, "transient", False)},
            )
            result = await self.fallback.assess(incident, runbooks, prompt)
            fallback_used = True
            provider_used = self.fallback.name
            LLM_FALLBACK.labels(self.primary.name, self.fallback.name).inc()
            await self._record_event(
                "fallback_used", self.fallback.name, {"primary": self.primary.name}
            )

        return AnalysisOutcome(
            assessment=result,
            runbooks=runbooks,
            provider_used=provider_used,
            fallback_used=fallback_used,
            cache_hit=False,
            processing_time_ms=int((perf_counter() - started) * 1000),
        )
