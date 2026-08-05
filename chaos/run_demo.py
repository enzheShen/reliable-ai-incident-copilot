# ruff: noqa: S310, UP017, UP032

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from reset_toxics import reset
from toxiproxy import add_toxic

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MOCK_PROXY_URL = os.getenv("MOCK_PROXY_URL", "http://localhost:8666")
LATENCY_MS = int(os.getenv("CHAOS_LATENCY_MS", "15000"))
REPORT_DIR = Path(__file__).parents[1] / "reports/chaos"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(method, url, payload=None, timeout=10):
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local demo endpoint
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def wait_for_json(url, timeout=90):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, body = request_json("GET", url, timeout=3)
            if status == 200:
                return body
        except Exception as exc:  # network state is the subject of this experiment
            last_error = exc
        time.sleep(1)
    raise RuntimeError("Timed out waiting for {}: {}".format(url, last_error))


def fallback_metric() -> float:
    with urlopen(BACKEND_URL + "/metrics", timeout=5) as response:  # noqa: S310
        text = response.read().decode()
    total = 0.0
    pattern = re.compile(r"^llm_fallback_total(?:\{[^}]*\})?\s+([0-9.eE+-]+)$")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            total += float(match.group(1))
    return total


def incident_payload():
    return {
        "service_name": "chaos-demo-api",
        "environment": "staging",
        "started_at": now(),
        "symptoms": "The mock upstream dependency exceeds its response deadline.",
        "logs": ["upstream gateway timeout deadline exceeded"],
        "metrics": {"upstream_p95_ms": float(LATENCY_MS), "error_rate": 0.4},
        "recent_changes": ["controlled Toxiproxy latency experiment"],
        "reporter": "chaos-demo",
    }


def write_report(result):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    timeline = "\n".join(
        "- `{}` — {}".format(item["at"], item["event"]) for item in result["timeline"]
    )
    (REPORT_DIR / "latest.md").write_text(
        "# Provider latency chaos report\n\nStatus: **{}**\n\n".format(result["status"])
        + "Injected latency: **{} ms**\n\n".format(result["latency_ms"])
        + "Fallback metric: **{} → {}**\n\n".format(
            result.get("fallback_metric_before"), result.get("fallback_metric_after")
        )
        + "Provider used: **{}**\n\n".format(result.get("provider_used", "not reached"))
        + "## Timeline\n\n{}\n\n".format(timeline)
        + "## Evidence\n\n```json\n{}\n```\n".format(
            json.dumps(result.get("assessment", {}), indent=2)
        ),
        encoding="utf-8",
    )


def main() -> None:
    result = {
        "started_at": now(),
        "status": "failed",
        "latency_ms": LATENCY_MS,
        "timeline": [],
    }

    def record(event):
        result["timeline"].append({"at": now(), "event": event})

    try:
        reset()
        record("Removed existing provider toxics")
        ready = wait_for_json(BACKEND_URL + "/health/ready")
        if ready.get("status") != "ready":
            raise RuntimeError("Backend was not ready before experiment")
        wait_for_json(MOCK_PROXY_URL + "/health")
        record("Backend and mock provider confirmed healthy")
        result["fallback_metric_before"] = fallback_metric()

        add_toxic("provider_latency", "latency", {"latency": LATENCY_MS, "jitter": 0})
        record("Injected downstream provider latency")
        started = time.monotonic()
        status, assessment = request_json(
            "POST",
            BACKEND_URL + "/api/v1/incidents/analyse",
            incident_payload(),
            timeout=60,
        )
        result["request_duration_seconds"] = round(time.monotonic() - started, 3)
        result["assessment"] = assessment
        if status != 200:
            raise RuntimeError("Analysis returned HTTP {}".format(status))
        if not assessment.get("fallback_used"):
            raise RuntimeError("Analysis did not use fallback")
        if assessment.get("provider_used") != "rule-based-fallback":
            raise RuntimeError("Unexpected fallback provider")
        if not assessment.get("requires_human_escalation"):
            raise RuntimeError("Fallback did not require human escalation")
        result["provider_used"] = assessment["provider_used"]
        record("Timeout and retry path returned validated rule-based fallback")
        result["fallback_metric_after"] = fallback_metric()
        if result["fallback_metric_after"] < result["fallback_metric_before"] + 1:
            raise RuntimeError("Prometheus fallback metric did not increase")
        record("Prometheus fallback counter increase verified")
        result["status"] = "passed"
    except Exception as exc:
        result["error"] = "{}: {}".format(type(exc).__name__, exc)
        record("Experiment failed: {}".format(result["error"]))
        raise
    finally:
        try:
            reset()
            wait_for_json(BACKEND_URL + "/health/ready")
            wait_for_json(MOCK_PROXY_URL + "/health")
            record("Toxics removed and dependency health restored")
        except Exception as cleanup_error:
            result["cleanup_error"] = "{}: {}".format(type(cleanup_error).__name__, cleanup_error)
            result["status"] = "failed"
            record("Cleanup verification failed")
        result["finished_at"] = now()
        write_report(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
