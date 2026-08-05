from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LatencyPoint(BaseModel):
    time: str
    p50: int
    p95: int


class ReliabilitySummary(BaseModel):
    window_minutes: int
    request_count: int
    success_rate: float = Field(ge=0, le=1)
    p50_latency_ms: int
    p95_latency_ms: int
    fallback_count: int
    cache_hit_rate: float = Field(ge=0, le=1)
    provider_failure_count: int
    severity_distribution: dict[str, int]
    latency_series: list[LatencyPoint]


class ReliabilityEventResponse(BaseModel):
    id: UUID
    event_type: str
    provider: str | None
    details: dict[str, object]
    created_at: datetime
