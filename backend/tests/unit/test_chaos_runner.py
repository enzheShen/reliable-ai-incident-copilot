import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "chaos/run_demo.py").exists()
)
sys.path.insert(0, str(PROJECT_ROOT))
run_demo = importlib.import_module("chaos.run_demo")


def test_cleanup_failure_writes_failed_report_and_exits_nonzero(monkeypatch, tmp_path) -> None:
    reset_calls = 0

    def reset_with_cleanup_failure() -> None:
        nonlocal reset_calls
        reset_calls += 1
        if reset_calls == 2:
            raise RuntimeError("synthetic cleanup failure")

    metric_values = iter((0.0, 0.0, 1.0, 1.0))
    assessment = {
        "fallback_used": True,
        "provider_used": "rule-based-fallback",
        "requires_human_escalation": True,
    }
    monkeypatch.setattr(run_demo, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(run_demo, "reset", reset_with_cleanup_failure)
    monkeypatch.setattr(run_demo, "wait_for_json", lambda url: {"status": "ready"})
    monkeypatch.setattr(run_demo, "metric_total", lambda name: next(metric_values))
    monkeypatch.setattr(run_demo, "add_toxic", lambda *args: None)
    monkeypatch.setattr(run_demo, "request_json", lambda *args, **kwargs: (200, assessment))

    with pytest.raises(RuntimeError, match="synthetic cleanup failure"):
        run_demo.main()

    report = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["toxic_cleanup_verified"] is False
    assert report["cleanup_error"] == "RuntimeError: synthetic cleanup failure"
