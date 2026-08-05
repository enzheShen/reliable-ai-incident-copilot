# ruff: noqa: UP017

import csv
import json
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODE = os.environ["LOAD_MODE"]
REPORT_DIR = ROOT / "reports" / "loadtests" / MODE
METRIC_LINE = re.compile(r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{.*\})? (?P<value>[-+0-9.eE]+)$")


def metric_total(path: Path, name: str) -> float:
    total = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        match = METRIC_LINE.match(line)
        if match and match.group("name") == name:
            total += float(match.group("value"))
    return total


def metric_delta(name: str) -> int:
    before = metric_total(REPORT_DIR / "metrics-before.prom", name)
    after = metric_total(REPORT_DIR / "metrics-after.prom", name)
    return round(after - before)


def main() -> None:
    metrics_before = REPORT_DIR / "metrics-before.prom"
    metrics_after = REPORT_DIR / "metrics-after.prom"
    observed_wall_clock_seconds = round(
        metrics_after.stat().st_mtime - metrics_before.stat().st_mtime, 3
    )
    with (REPORT_DIR / "latest_stats.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    aggregate = next(row for row in rows if row["Name"] == "Aggregated")
    request_count = int(aggregate["Request Count"])
    failures = int(aggregate["Failure Count"])
    cache_hits = metric_delta("cache_hits_total")
    cache_misses = metric_delta("cache_misses_total")
    cache_total = cache_hits + cache_misses
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": MODE,
        "mode_description": (
            "unique synthetic incidents exercising the HTTP mock-provider path"
            if MODE == "cold"
            else "fixed 60-fixture set exercising the assessment-cache path after warm-up"
        ),
        "users": int(os.getenv("LOAD_USERS", "20")),
        "duration": os.getenv("LOAD_DURATION", "5m"),
        "observed_wall_clock_seconds": observed_wall_clock_seconds,
        "request_count": request_count,
        "failure_count": failures,
        "error_rate": round(failures / request_count, 6) if request_count else 0.0,
        "throughput_requests_per_second": float(aggregate["Requests/s"]),
        "p50_latency_ms": float(aggregate["50%"]),
        "p95_latency_ms": float(aggregate["95%"]),
        "p99_latency_ms": float(aggregate["99%"]),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate": round(cache_hits / cache_total, 6) if cache_total else 0.0,
        "provider_request_count": metric_delta("llm_requests_total"),
        "fallback_count": metric_delta("llm_fallback_total"),
        "environment": "local Docker Desktop; not a production capacity measurement",
        "machine_platform": platform.platform(),
        "data_classification": "checked-in synthetic fixtures only",
        "runtime_note": (
            "Throughput is the unadjusted Locust wall-clock value. A wall-clock interval above "
            "the configured duration indicates a local host or Docker scheduling pause."
        ),
    }
    (REPORT_DIR / "latest.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "latest.md").write_text(
        f"# {MODE.title()} load-test report\n\n"
        f"Generated at `{result['generated_at']}` with {result['users']} users for "
        f"{result['duration']}. This was the {result['mode_description']}.\n\n"
        "| Metric | Result |\n| --- | ---: |\n"
        f"| Requests | {request_count} |\n"
        f"| Observed wall clock | {observed_wall_clock_seconds} seconds |\n"
        f"| Failures | {failures} |\n"
        f"| Error rate | {result['error_rate']} |\n"
        f"| Throughput | {result['throughput_requests_per_second']} req/s |\n"
        f"| p50 HTTP latency | {result['p50_latency_ms']} ms |\n"
        f"| p95 HTTP latency | {result['p95_latency_ms']} ms |\n"
        f"| p99 HTTP latency | {result['p99_latency_ms']} ms |\n"
        f"| Cache hits | {cache_hits} |\n"
        f"| Cache misses | {cache_misses} |\n"
        f"| Cache hit rate | {result['cache_hit_rate']} |\n"
        f"| Provider requests | {result['provider_request_count']} |\n"
        f"| Fallbacks | {result['fallback_count']} |\n\n"
        "## Scope\n\n"
        "The test ran on local Docker Desktop with checked-in synthetic data. "
        "It is not a production capacity or achieved-uptime measurement. Throughput is Locust's "
        "unadjusted wall-clock value; a longer observed wall clock records local host or Docker "
        "scheduling pauses rather than hiding them.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    if MODE == "cold" and result["cache_hit_rate"] >= 0.05:
        raise SystemExit("cold cache-hit rate must remain below 5%")
    if MODE == "warm" and result["cache_hit_rate"] <= 0.90:
        raise SystemExit("warm cache-hit rate must exceed 90%")


if __name__ == "__main__":
    main()
