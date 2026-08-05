from datetime import datetime
from enum import StrEnum
from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
T = TypeVar("T")


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Severity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(StrEnum):
    PENDING = "pending"
    ASSESSED = "assessed"


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    environment: Environment
    started_at: datetime
    symptoms: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=10_000)
    ]
    logs: Annotated[
        list[Annotated[str, StringConstraints(max_length=2_000)]], Field(max_length=100)
    ]
    metrics: dict[Annotated[str, StringConstraints(min_length=1, max_length=100)], float]
    recent_changes: Annotated[
        list[Annotated[str, StringConstraints(max_length=500)]], Field(max_length=50)
    ]
    reporter: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        return value

    @field_validator("metrics")
    @classmethod
    def limit_metrics(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) > 100:
            raise ValueError("at most 100 metrics are allowed")
        return value


class RunbookReference(BaseModel):
    id: UUID
    title: str
    relevance: Annotated[float, Field(ge=0, le=1)]


class IncidentAssessment(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    incident_id: UUID
    severity: Severity
    summary: str
    likely_causes: list[str]
    evidence: list[str]
    recommended_actions: list[str]
    runbook_references: list[RunbookReference]
    confidence: Annotated[float, Field(ge=0, le=1)]
    requires_human_escalation: bool
    provider_used: str
    fallback_used: bool
    processing_time_ms: Annotated[int, Field(ge=0)]
    created_at: datetime
    cache_hit: bool = False


class IncidentHistoryItem(BaseModel):
    id: UUID
    service_name: str
    environment: Environment
    started_at: datetime
    created_at: datetime
    status: IncidentStatus
    severity: Severity | None
    summary: str | None


class IncidentDetail(BaseModel):
    incident: IncidentCreate
    id: UUID
    created_at: datetime
    assessment: IncidentAssessment | None


class PaginatedResponse(BaseModel, Generic[T]):
    page: int
    page_size: int
    total: int
    items: list[T]


IncidentPage = PaginatedResponse[IncidentHistoryItem]
