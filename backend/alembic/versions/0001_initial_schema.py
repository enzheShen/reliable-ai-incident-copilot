"""Create incident copilot schema.

Revision ID: 0001
Revises:
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("logs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recent_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reporter", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
    )
    op.create_index(op.f("ix_incidents_service_name"), "incidents", ["service_name"])
    op.create_table(
        "runbooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=384), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runbooks")),
    )
    op.create_index(op.f("ix_runbooks_slug"), "runbooks", ["slug"], unique=True)
    op.create_table(
        "reliability_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reliability_events")),
    )
    op.create_index(op.f("ix_reliability_events_event_type"), "reliability_events", ["event_type"])
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("severity", sa.String(length=4), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("likely_causes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("requires_human_escalation", sa.Boolean(), nullable=False),
        sa.Column("provider_used", sa.String(length=80), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_assessments_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
        sa.UniqueConstraint("incident_id", name=op.f("uq_assessments_incident_id")),
    )
    op.create_index(
        "ix_assessments_created_at", "assessments", [sa.literal_column("created_at DESC")]
    )
    op.create_index(op.f("ix_assessments_incident_id"), "assessments", ["incident_id"])
    op.create_index(op.f("ix_assessments_severity"), "assessments", ["severity"])
    op.create_table(
        "assessment_runbooks",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("runbook_id", sa.Uuid(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_assessment_runbooks_assessment_id_assessments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["runbook_id"],
            ["runbooks.id"],
            name=op.f("fk_assessment_runbooks_runbook_id_runbooks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("assessment_id", "runbook_id", name=op.f("pk_assessment_runbooks")),
        sa.UniqueConstraint(
            "assessment_id", "runbook_id", name=op.f("uq_assessment_runbooks_assessment_id")
        ),
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_idempotency_keys_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_idempotency_keys")),
        sa.UniqueConstraint("incident_id", name=op.f("uq_idempotency_keys_incident_id")),
    )
    op.create_index(op.f("ix_idempotency_keys_expires_at"), "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("assessment_runbooks")
    op.drop_table("assessments")
    op.drop_table("reliability_events")
    op.drop_table("runbooks")
    op.drop_table("incidents")
    op.execute("DROP EXTENSION IF EXISTS vector")
