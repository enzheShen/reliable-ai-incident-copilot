from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas import IncidentCreate


def valid_payload() -> dict[str, object]:
    return {
        "service_name": "checkout-api",
        "environment": "production",
        "started_at": datetime(2026, 8, 5, 10, 30, tzinfo=UTC),
        "symptoms": "Requests are timing out for a subset of users.",
        "logs": ["upstream timeout after 2000ms"],
        "metrics": {"p95_latency_ms": 2450.0, "error_rate": 0.12},
        "recent_changes": ["release 1.4.2"],
        "reporter": "synthetic-monitor",
    }


def test_incident_create_accepts_valid_payload() -> None:
    incident = IncidentCreate.model_validate(valid_payload())
    assert incident.environment.value == "production"
    assert incident.metrics["error_rate"] == 0.12


def test_incident_create_rejects_unknown_field() -> None:
    payload = valid_payload()
    payload["unexpected_field"] = "must-not-pass"
    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(payload)


def test_incident_create_requires_timezone() -> None:
    payload = valid_payload()
    payload["started_at"] = datetime(2026, 8, 5, 10, 30)
    with pytest.raises(ValidationError, match="timezone"):
        IncidentCreate.model_validate(payload)


def test_incident_create_limits_log_length() -> None:
    payload = valid_payload()
    payload["logs"] = ["x" * 2_001]
    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(payload)
