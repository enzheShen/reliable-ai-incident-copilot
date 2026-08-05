# ruff: noqa: UP017

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(__file__).parents[1] / "reports/loadtests"


def main() -> None:
    with (REPORT_DIR / "latest_stats.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    aggregate = next(row for row in rows if row["Name"] == "Aggregated")
    request_count = int(aggregate["Request Count"])
    failures = int(aggregate["Failure Count"])
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "users": int(os.getenv("LOAD_USERS", "20")),
        "duration": os.getenv("LOAD_DURATION", "5m"),
        "request_count": request_count,
        "failure_count": failures,
        "error_rate": round(failures / request_count, 6) if request_count else 0.0,
        "throughput_requests_per_second": float(aggregate["Requests/s"]),
        "p50_latency_ms": float(aggregate["50%"]),
        "p95_latency_ms": float(aggregate["95%"]),
        "p99_latency_ms": float(aggregate["99%"]),
    }
    (REPORT_DIR / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (REPORT_DIR / "latest.md").write_text(
        "# Load-test report\n\n"
        f"Generated at `{result['generated_at']}` with {result['users']} users for "
        f"{result['duration']} in mock mode.\n\n"
        "| Metric | Result |\n| --- | ---: |\n"
        f"| Requests | {request_count} |\n"
        f"| Throughput | {result['throughput_requests_per_second']} req/s |\n"
        f"| Error rate | {result['error_rate']} |\n"
        f"| p50 | {result['p50_latency_ms']} ms |\n"
        f"| p95 | {result['p95_latency_ms']} ms |\n"
        f"| p99 | {result['p99_latency_ms']} ms |\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
