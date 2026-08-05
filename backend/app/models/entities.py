from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Incident(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "incidents"

    service_name: Mapped[str] = mapped_column(String(100), index=True)
    environment: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    symptoms: Mapped[str] = mapped_column(Text)
    logs: Mapped[list[str]] = mapped_column(JSONB)
    metrics: Mapped[dict[str, float]] = mapped_column(JSONB)
    recent_changes: Mapped[list[str]] = mapped_column(JSONB)
    reporter: Mapped[str | None] = mapped_column(String(120))
    assessment: Mapped[Assessment | None] = relationship(
        back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )


class Assessment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "assessments"

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, index=True
    )
    severity: Mapped[str] = mapped_column(String(4), index=True)
    summary: Mapped[str] = mapped_column(Text)
    likely_causes: Mapped[list[str]] = mapped_column(JSONB)
    evidence: Mapped[list[str]] = mapped_column(JSONB)
    recommended_actions: Mapped[list[str]] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float)
    requires_human_escalation: Mapped[bool] = mapped_column(Boolean)
    provider_used: Mapped[str] = mapped_column(String(80))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer)
    incident: Mapped[Incident] = relationship(back_populates="assessment")
    runbook_links: Mapped[list[AssessmentRunbook]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Runbook(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "runbooks"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    assessment_links: Mapped[list[AssessmentRunbook]] = relationship(back_populates="runbook")


class AssessmentRunbook(Base):
    __tablename__ = "assessment_runbooks"
    __table_args__ = (UniqueConstraint("assessment_id", "runbook_id"),)

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True
    )
    runbook_id: Mapped[UUID] = mapped_column(
        ForeignKey("runbooks.id", ondelete="RESTRICT"), primary_key=True
    )
    relevance_score: Mapped[float] = mapped_column(Float)
    assessment: Mapped[Assessment] = relationship(back_populates="runbook_links")
    runbook: Mapped[Runbook] = relationship(back_populates="assessment_links")


class ReliabilityEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reliability_events"

    event_type: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict[str, object]] = mapped_column(JSONB)


class IdempotencyKey(CreatedAtMixin, Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


Index("ix_assessments_created_at", Assessment.created_at.desc())
