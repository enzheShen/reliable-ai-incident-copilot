import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
REPORT_DIR = ROOT / "reports" / "loadtests"


def row(result: dict[str, Any]) -> str:
    return (
        f"| {result['mode']} | {result['request_count']} | {result['failure_count']} | "
        f"{result['throughput_requests_per_second']} | {result['p50_latency_ms']} | "
        f"{result['p95_latency_ms']} | {result['p99_latency_ms']} | "
        f"{result['cache_hit_rate']} | {result['provider_request_count']} | "
        f"{result['fallback_count']} |"
    )


def main() -> None:
    cold = json.loads((REPORT_DIR / "cold" / "latest.json").read_text(encoding="utf-8"))
    warm = json.loads((REPORT_DIR / "warm" / "latest.json").read_text(encoding="utf-8"))
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cold": cold,
        "warm": warm,
        "interpretation": (
            "Cold exercises unique provider-path requests; warm repeats 60 fixtures to measure "
            "the cache path. The modes provide separate evidence and are not interchangeable."
        ),
    }
    (REPORT_DIR / "comparison.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "comparison.md").write_text(
        "# Cold and warm load-test comparison\n\n"
        "| Mode | Requests | Failures | req/s | p50 ms | p95 ms | p99 ms | Cache-hit rate | Provider requests | Fallbacks |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
        f"{row(cold)}\n{row(warm)}\n\n"
        "Cold uses a unique synthetic reporter and idempotency key for every request, while warm "
        "repeats the fixed 60-fixture dataset after clearing Redis. These local Docker measurements "
        "are separate path-specific evidence, not production capacity or achieved uptime.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
