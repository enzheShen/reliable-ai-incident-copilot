from datetime import UTC, datetime

import pytest

from app.providers import ProviderError
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.safety import apply_provider_safety_policy


def incident() -> IncidentCreate:
    return IncidentCreate(
        service_name="orders-api",
        environment="production",
        started_at=datetime(2026, 8, 5, tzinfo=UTC),
        symptoms="Checkout requests exceed the latency objective.",
        logs=["slow request route=/checkout duration=2400ms"],
        metrics={"p95_latency_ms": 2400.0},
        recent_changes=["release 1.4.2"],
    )


def assessment(**updates: object) -> ProviderAssessment:
    values: dict[str, object] = {
        "severity": "SEV3",
        "summary": "Checkout latency is elevated.",
        "likely_causes": ["A recent release"],
        "evidence": ["slow request route=/checkout duration=2400ms"],
        "recommended_actions": ["Inspect route latency"],
        "confidence": 0.9,
        "requires_human_escalation": False,
    }
    values.update(updates)
    return ProviderAssessment.model_validate(values)


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({"severity": "SEV1"}, True),
        ({"severity": "SEV2"}, True),
        ({"confidence": 0.69}, True),
        ({"severity": "SEV3", "confidence": 0.7}, False),
    ],
)
def test_deterministic_escalation_policy(updates: dict[str, object], expected: bool) -> None:
    result = apply_provider_safety_policy(incident(), assessment(**updates))
    assert result.requires_human_escalation is expected


def test_fallback_always_escalates() -> None:
    result = apply_provider_safety_policy(incident(), assessment(), fallback=True)
    assert result.requires_human_escalation is True


def test_ungrounded_provider_evidence_is_rejected() -> None:
    with pytest.raises(ProviderError, match="not grounded"):
        apply_provider_safety_policy(
            incident(),
            assessment(evidence=["The database has exhausted every connection"]),
        )


def test_metric_evidence_is_grounded() -> None:
    result = apply_provider_safety_policy(
        incident(), assessment(evidence=["p95_latency_ms=2400"])
    )
    assert result.evidence == ["p95_latency_ms=2400"]
