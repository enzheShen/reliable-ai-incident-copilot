from app.evaluation import regression_evaluate


def test_mock_evaluation_is_reproducible_and_complete() -> None:
    result = regression_evaluate()
    assert result["evaluation_type"] == "deterministic-regression"
    assert result["execution"] == "in-memory"
    assert result["http_provider_used"] is False
    assert result["database_used"] is False
    assert result["cases"] == 60
    assert result["severity_accuracy"] == 1.0
    assert result["runbook_recall_at_1"] == 1.0
    assert result["runbook_recall_at_3"] == 1.0
    assert result["serialized_output_validation_rate"] == 1.0
    assert result["escalation_accuracy"] == 1.0
    assert result["average_in_memory_processing_time_ms"] >= 0
    assert result["live_anthropic"]["status"] in {"skipped", "not_run"}
