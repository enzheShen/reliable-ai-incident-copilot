from fastapi.testclient import TestClient

from app.logging import redact_mapping
from app.main import create_app
from app.observability.middleware import normalized_path


def test_sensitive_fields_are_redacted_recursively() -> None:
    value = redact_mapping(
        {
            "Authorization": "Bearer example",
            "nested": {"api_key": "example", "safe": "visible"},
            "cookie": "session=example",
        }
    )
    assert value == {
        "Authorization": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "safe": "visible"},
        "cookie": "[REDACTED]",
    }


def test_uuid_paths_are_normalized_for_metric_labels() -> None:
    assert (
        normalized_path("/api/v1/incidents/47f0db93-aee9-4278-afc1-c24655497805")
        == "/api/v1/incidents/{incident_id}"
    )


def test_liveness_correlation_metrics_and_body_limit() -> None:
    with TestClient(create_app()) as client:
        live = client.get("/health/live", headers={"X-Correlation-ID": "test-request-1"})
        assert live.status_code == 200
        assert live.headers["X-Correlation-ID"] == "test-request-1"
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        required = [
            "http_requests_total",
            "http_request_duration_seconds",
            "llm_requests_total",
            "llm_request_duration_seconds",
            "llm_failures_total",
            "llm_fallback_total",
            "circuit_breaker_state",
            "cache_hits_total",
            "cache_misses_total",
            "incident_assessments_total",
            "readiness_check_failures_total",
        ]
        for metric in required:
            assert metric in metrics.text
        too_large = client.post(
            "/api/v1/incidents/analyse",
            content="x" * 65_537,
            headers={"Content-Type": "application/json"},
        )
        assert too_large.status_code == 413
