"""Generate the checked-in deterministic runbook and synthetic incident datasets."""

# Fixture prose stays on one line so regenerated JSON remains easy to diff.
# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RUNBOOKS = [
    {
        "id": "00000000-0000-4000-8000-000000000001",
        "slug": "api-latency-spike",
        "title": "API latency spike",
        "keywords": ["latency", "p95", "slow request", "timeout"],
        "content": "Confirm p50/p95 by route and compare error rate with the last healthy window. Check downstream timings and saturation before scaling. Roll back a correlated release when evidence supports it; otherwise shed optional work and capture traces.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000002",
        "slug": "database-connection-saturation",
        "title": "Database connection saturation",
        "keywords": ["database", "connection pool", "too many clients", "pool timeout"],
        "content": "Inspect active, idle, and waiting database sessions plus pool checkout time. Stop connection leaks or expensive callers before increasing limits. Protect the database with bounded pools, terminate only verified abandoned sessions, and validate query latency after recovery.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000003",
        "slug": "redis-outage",
        "title": "Redis outage",
        "keywords": ["redis", "cache", "connection refused", "readonly"],
        "content": "Check Redis reachability, role, memory, and recent failover events. Disable nonessential cache traffic and use the documented degraded path. Restore the correct primary, verify writes and expiry, then reintroduce traffic gradually to avoid a cache stampede.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000004",
        "slug": "authentication-failure",
        "title": "Authentication failure",
        "keywords": ["authentication", "401", "token", "signature", "jwks"],
        "content": "Segment failures by client, issuer, and token validation reason without logging tokens. Verify clock skew, signing-key publication, and issuer configuration. Restore the last known key/configuration if a rotation caused the issue and require security review for unexplained failures.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000005",
        "slug": "rate-limit-spike",
        "title": "Rate-limit spike",
        "keywords": ["rate limit", "429", "quota", "throttle"],
        "content": "Identify the clients and routes consuming quota and confirm whether traffic is legitimate. Preserve protective limits during dependency saturation. Apply a scoped temporary quota only with capacity evidence, communicate retry guidance, and monitor rejection and saturation together.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000006",
        "slug": "upstream-dependency-timeout",
        "title": "Upstream dependency timeout",
        "keywords": ["upstream", "dependency", "deadline exceeded", "gateway timeout", "504"],
        "content": "Measure upstream latency and timeout rates by operation. Confirm client deadlines and retry amplification. Open the circuit or use a safe fallback, reduce nonessential calls, and contact the dependency owner with correlation IDs and measured windows.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000007",
        "slug": "memory-leak",
        "title": "Memory leak",
        "keywords": ["memory", "oom", "heap", "rss", "out of memory"],
        "content": "Compare resident memory and heap growth against traffic and release time. Capture a bounded profile before restart when safe. Roll back a correlated build, restart instances gradually to protect capacity, and add a regression test for the retained allocation path.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000008",
        "slug": "cpu-saturation",
        "title": "CPU saturation",
        "keywords": ["cpu", "load average", "throttling", "run queue"],
        "content": "Check CPU by instance, process, and request route alongside throttling and run queue. Identify hot loops or expensive requests with a short profile. Shed optional work, roll back a correlated change, or scale within known limits, then confirm latency recovery.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000009",
        "slug": "disk-capacity-exhaustion",
        "title": "Disk capacity exhaustion",
        "keywords": ["disk", "no space left", "inode", "filesystem"],
        "content": "Check bytes and inode usage by mount, then locate the fastest-growing safe-to-inspect paths. Stop unbounded writers and rotate disposable logs using retention policy. Expand capacity only after controlling growth and verify database durability before deleting data.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000010",
        "slug": "message-queue-backlog",
        "title": "Message queue backlog",
        "keywords": ["queue", "backlog", "consumer lag", "oldest message"],
        "content": "Measure queue depth, oldest-message age, publish rate, and consumer success. Identify poison messages or a stalled consumer before scaling. Pause noncritical publishers, quarantine verified poison messages, and increase consumers only when downstream capacity is safe.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000011",
        "slug": "tls-certificate-expiry",
        "title": "TLS certificate expiry",
        "keywords": ["tls", "certificate", "x509", "expired", "handshake"],
        "content": "Confirm the certificate chain, expiry, hostname, and affected endpoints from a trusted probe. Renew through the approved issuer, deploy the full chain, and verify from multiple clients. Never bypass certificate validation as a mitigation; add expiry alerting after recovery.",
    },
    {
        "id": "00000000-0000-4000-8000-000000000012",
        "slug": "deployment-regression",
        "title": "Deployment regression",
        "keywords": ["deployment", "release", "rollback", "regression", "new version"],
        "content": "Correlate error, latency, and resource changes with rollout cohorts. Freeze the rollout and compare old and new versions. Roll back through the standard deployment path when causality is strong, verify recovery, and preserve logs and the minimal failing case.",
    },
]

TEMPLATES = [
    ("api-latency-spike", "SEV2", "API p95 latency rose above 2400ms", "slow request route=/v1/orders duration=2480ms", {"p95_latency_ms": 2480.0, "error_rate": 0.08}, ["latency", "p95"], True),
    ("database-connection-saturation", "SEV1", "Database requests cannot acquire pooled connections", "pool timeout: too many clients waiting", {"db_pool_used_ratio": 0.99, "error_rate": 0.31}, ["pool", "too many clients"], True),
    ("redis-outage", "SEV2", "Cache and rate-limit operations are failing", "redis connection refused at cache endpoint", {"cache_error_rate": 0.72, "cache_hit_rate": 0.01}, ["redis", "connection refused"], True),
    ("authentication-failure", "SEV1", "Most production sign-ins return 401", "token signature validation failed against jwks", {"http_401_rate": 0.64, "login_success_rate": 0.21}, ["401", "signature"], True),
    ("rate-limit-spike", "SEV3", "Clients are receiving an unusual burst of 429 responses", "quota throttle applied route=/search status=429", {"http_429_rate": 0.18, "requests_per_second": 720.0}, ["429", "quota"], False),
    ("upstream-dependency-timeout", "SEV2", "Payment dependency calls exceed their deadline", "upstream gateway timeout status=504 deadline exceeded", {"upstream_p95_ms": 12100.0, "error_rate": 0.27}, ["upstream", "504"], True),
    ("memory-leak", "SEV2", "Worker memory grows continuously until restart", "process killed: out of memory rss=1950mb", {"rss_mb": 1950.0, "restart_count": 7.0}, ["memory", "rss"], True),
    ("cpu-saturation", "SEV2", "API instances are CPU saturated with rising latency", "cpu throttling detected run queue=18", {"cpu_utilization": 0.98, "p95_latency_ms": 1820.0}, ["cpu", "throttling"], True),
    ("disk-capacity-exhaustion", "SEV1", "Writes fail because the data volume is full", "write failed: no space left on device", {"disk_used_ratio": 1.0, "free_inodes_ratio": 0.02}, ["disk", "no space left"], True),
    ("message-queue-backlog", "SEV2", "Event processing is delayed by a growing queue", "consumer lag high oldest message age=1800s", {"queue_depth": 48000.0, "oldest_message_seconds": 1800.0}, ["consumer lag", "queue"], True),
    ("tls-certificate-expiry", "SEV1", "External clients cannot complete TLS handshakes", "x509 certificate has expired during tls handshake", {"tls_failure_rate": 0.88, "successful_connections": 12.0}, ["certificate", "expired"], True),
    ("deployment-regression", "SEV2", "Error rate increased immediately after a new release", "new version 2.8.0 exception rate regression", {"error_rate": 0.24, "healthy_instances_ratio": 0.55}, ["new version", "regression"], True),
]

HELD_OUT_CASES = [
    {
        "incident_input": {
            "service_name": "checkout-edge",
            "environment": "production",
            "started_at": "2026-02-03T14:05:00Z",
            "symptoms": "Checkout requests remain successful but tail response time tripled across two regions.",
            "logs": ["slow request route=/checkout duration=3180ms region=eu-west", "trace_sample=synthetic-latency-01"],
            "metrics": {"p95_latency_ms": 3180.0, "p50_latency_ms": 410.0, "error_rate": 0.03},
            "recent_changes": ["Enabled a synthetic pricing middleware experiment for 10 percent of traffic."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000001",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "catalog-writer",
            "environment": "production",
            "started_at": "2026-02-04T08:12:00Z",
            "symptoms": "Write workers are waiting for database pool checkout and new jobs are timing out.",
            "logs": ["pool timeout after 5000ms waiting=83 active=40", "database reports too many clients for role catalog"],
            "metrics": {"db_pool_used_ratio": 1.0, "pool_waiters": 83.0, "write_error_rate": 0.36},
            "recent_changes": ["Synthetic batch import concurrency changed from 8 to 32."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV1",
        "expected_runbook": "00000000-0000-4000-8000-000000000002",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "session-store-client",
            "environment": "staging",
            "started_at": "2026-02-05T19:40:00Z",
            "symptoms": "Sessions fall back to the degraded path because cache writes cannot reach Redis.",
            "logs": ["redis connection refused host=cache-primary port=6379", "degraded session mode enabled synthetic=true"],
            "metrics": {"cache_write_error_rate": 0.81, "cache_hit_rate": 0.04},
            "recent_changes": ["A synthetic failover rehearsal promoted a replica in staging."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000003",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "identity-gateway",
            "environment": "production",
            "started_at": "2026-02-06T06:25:00Z",
            "symptoms": "Mobile clients cannot authenticate after a signing-key rotation and receive HTTP 401.",
            "logs": ["token signature validation failed issuer=synthetic-idp", "jwks key id not found status=401"],
            "metrics": {"http_401_rate": 0.71, "authentication_success_rate": 0.17},
            "recent_changes": ["Rotated the synthetic identity provider signing key."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV1",
        "expected_runbook": "00000000-0000-4000-8000-000000000004",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "public-search",
            "environment": "production",
            "started_at": "2026-02-07T11:55:00Z",
            "symptoms": "One synthetic client cohort is exhausting its search quota and seeing throttled responses.",
            "logs": ["rate limit applied client=synthetic-load status=429", "quota bucket search-read exhausted"],
            "metrics": {"http_429_rate": 0.22, "requests_per_second": 910.0},
            "recent_changes": ["Started an approved synthetic traffic replay for the search route."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV3",
        "expected_runbook": "00000000-0000-4000-8000-000000000005",
        "escalation_expected": False,
    },
    {
        "incident_input": {
            "service_name": "invoice-orchestrator",
            "environment": "production",
            "started_at": "2026-02-08T16:30:00Z",
            "symptoms": "Invoice generation blocks while the tax dependency exceeds the caller deadline.",
            "logs": ["upstream tax dependency gateway timeout status=504", "deadline exceeded operation=calculate-tax"],
            "metrics": {"upstream_p95_ms": 14350.0, "dependency_timeout_rate": 0.29},
            "recent_changes": ["No application release; synthetic dependency latency was injected."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000006",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "document-renderer",
            "environment": "staging",
            "started_at": "2026-02-09T22:10:00Z",
            "symptoms": "Renderer resident memory increases after each synthetic document and pods eventually restart.",
            "logs": ["out of memory kill container=renderer rss=2280mb", "heap retained allocation grew by 420mb"],
            "metrics": {"rss_mb": 2280.0, "restart_count": 9.0, "heap_growth_mb_per_hour": 420.0},
            "recent_changes": ["Upgraded the synthetic PDF parsing library in the staging image."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000007",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "recommendation-api",
            "environment": "production",
            "started_at": "2026-02-10T13:48:00Z",
            "symptoms": "All recommendation workers are CPU bound and request queues are growing.",
            "logs": ["cpu throttling 92 percent container=recommender", "run queue length=24 hot_loop=synthetic"],
            "metrics": {"cpu_utilization": 0.99, "p95_latency_ms": 2070.0, "run_queue": 24.0},
            "recent_changes": ["Enabled a synthetic ranking feature on half of instances."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000008",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "audit-log-writer",
            "environment": "production",
            "started_at": "2026-02-11T03:35:00Z",
            "symptoms": "Durable audit writes stopped when the filesystem exhausted both capacity and inodes.",
            "logs": ["write failed no space left on device mount=/data", "filesystem inode allocation failed synthetic=true"],
            "metrics": {"disk_used_ratio": 1.0, "free_inodes_ratio": 0.0, "failed_writes": 1260.0},
            "recent_changes": ["A synthetic log generator bypassed its normal rotation threshold."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV1",
        "expected_runbook": "00000000-0000-4000-8000-000000000009",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "email-dispatch-consumer",
            "environment": "production",
            "started_at": "2026-02-12T17:02:00Z",
            "symptoms": "Transactional messages remain queued while consumer progress falls behind publishers.",
            "logs": ["consumer lag partitions=12 oldest message age=2460s", "queue backlog rising poison_message=not-confirmed"],
            "metrics": {"queue_depth": 73500.0, "oldest_message_seconds": 2460.0, "consumer_success_rate": 0.44},
            "recent_changes": ["Reduced synthetic consumer replicas during a capacity exercise."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000010",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "partner-webhook-edge",
            "environment": "production",
            "started_at": "2026-02-13T09:20:00Z",
            "symptoms": "Partner webhook clients reject the endpoint during the TLS handshake.",
            "logs": ["tls handshake failed x509 certificate has expired", "certificate hostname=synthetic-webhook.example invalid_after=2026-02-13"],
            "metrics": {"tls_failure_rate": 0.93, "successful_connections": 7.0},
            "recent_changes": ["Synthetic certificate renewal rehearsal intentionally left the old chain active."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV1",
        "expected_runbook": "00000000-0000-4000-8000-000000000011",
        "escalation_expected": True,
    },
    {
        "incident_input": {
            "service_name": "pricing-engine",
            "environment": "production",
            "started_at": "2026-02-14T18:45:00Z",
            "symptoms": "A canary release returns calculation errors while the previous cohort remains healthy.",
            "logs": ["new version=4.3.1 regression cohort=canary exception=decimal-overflow", "rollback candidate synthetic_release=true"],
            "metrics": {"canary_error_rate": 0.41, "stable_error_rate": 0.01, "healthy_instances_ratio": 0.58},
            "recent_changes": ["Deployed synthetic pricing version 4.3.1 to 20 percent of instances."],
            "reporter": "synthetic-evaluation",
        },
        "expected_severity": "SEV2",
        "expected_runbook": "00000000-0000-4000-8000-000000000012",
        "escalation_expected": True,
    },
]


def generate() -> tuple[
    list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]
]:
    incidents: list[dict[str, object]] = []
    evaluations: list[dict[str, object]] = []
    started = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    environments = ["production", "staging", "production", "production", "development"]
    for category_index, template in enumerate(TEMPLATES, start=1):
        slug, severity, symptoms, log, metrics, evidence, escalation = template
        runbook = next(item for item in RUNBOOKS if item["slug"] == slug)
        for variation in range(1, 6):
            fixture_id = category_index * 100 + variation
            incident = {
                "service_name": f"synthetic-service-{category_index:02d}",
                "environment": environments[variation - 1],
                "started_at": (started + timedelta(hours=fixture_id)).isoformat(),
                "symptoms": f"{symptoms}; synthetic scenario {variation}.",
                "logs": [f"{log} sample={variation}", "correlation_id=synthetic-only"],
                "metrics": {**metrics, "sample": float(variation)},
                "recent_changes": [f"synthetic change window {variation}"],
                "reporter": "synthetic-monitor",
            }
            fixture = {
                "fixture_id": f"incident-{fixture_id}",
                "incident": incident,
                "expected_severity": severity,
                "expected_runbook_id": runbook["id"],
                "expected_runbook_slug": slug,
                "expected_evidence_keywords": evidence,
                "expected_escalation": escalation,
            }
            incidents.append(fixture)
            evaluations.append(
                {
                    "incident_input": incident,
                    "expected_severity": severity,
                    "expected_runbook": runbook["id"],
                    "expected_evidence_keywords": evidence,
                    "escalation_expected": escalation,
                }
            )
    return incidents, evaluations, HELD_OUT_CASES


def main() -> None:
    incidents, evaluations, held_out = generate()
    (ROOT / "runbooks" / "runbooks.json").write_text(
        json.dumps(RUNBOOKS, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "incidents" / "synthetic-incidents.json").write_text(
        json.dumps(incidents, indent=2) + "\n", encoding="utf-8"
    )
    with (ROOT / "evaluation" / "evaluation.jsonl").open("w", encoding="utf-8") as output:
        for record in evaluations:
            output.write(json.dumps(record, separators=(",", ":")) + "\n")
    with (ROOT / "evaluation" / "held-out.jsonl").open("w", encoding="utf-8") as output:
        for record in held_out:
            output.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(
        f"generated {len(RUNBOOKS)} runbooks, {len(incidents)} incidents, "
        f"{len(evaluations)} regression cases, {len(held_out)} held-out cases"
    )


if __name__ == "__main__":
    main()
