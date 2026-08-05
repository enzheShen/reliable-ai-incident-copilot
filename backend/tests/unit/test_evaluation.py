from app.evaluation import evaluate


def test_mock_evaluation_is_reproducible_and_complete() -> None:
    result = evaluate()
    assert result["cases"] == 60
    assert result["severity_accuracy"] == 1.0
    assert result["runbook_recall_at_1"] == 1.0
    assert result["runbook_recall_at_3"] == 1.0
    assert result["valid_structured_output_rate"] == 1.0
    assert result["escalation_accuracy"] == 1.0
    assert result["live_anthropic"]["status"] in {"skipped", "not_run"}
