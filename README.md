# Reliable AI Incident Copilot

[![CI](https://github.com/enzheShen/reliable-ai-incident-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/enzheShen/reliable-ai-incident-copilot/actions/workflows/ci.yml)

A production-style portfolio project that turns structured service-incident telemetry into a validated, evidence-linked assessment and degrades explicitly when its AI provider fails.

![Incident assessment UI](docs/images/incident-analysis.png)

_Captured from the Docker Compose stack after a real mock-provider analysis; all incident data is synthetic._

## Why this project

Incident tooling is useful only when operators can distinguish evidence from inference and normal output from degraded output. This project explores that boundary in a compact full-stack system: runbook retrieval, strict LLM output validation, durable history, and the failure controls usually omitted from chatbot demos.

The repository is deliberately a modular monolith rather than a collection of premature services. It is intended to demonstrate graduate AI software, backend, platform, and reliability engineering skills without claiming production readiness or real-company usage.

## What it does

- Accepts a constrained incident JSON contract and ships six safe synthetic examples.
- Retrieves the top versioned runbooks from PostgreSQL with pgvector.
- Produces severity, summary, likely causes, evidence, actions, confidence, escalation, provider, and runbook references.
- Persists incident and assessment history with service, severity, and status filters.
- Exposes live reliability summaries, recent reliability events, health checks, and Prometheus metrics.
- Runs without a paid key through a deterministic HTTP mock provider.
- Supports optional Anthropic live mode without storing or logging the key.
- Includes deterministic evaluation, Locust workload, and Toxiproxy failure experiments.

## Architecture

```mermaid
flowchart LR
    U["Operator"] --> F["React + TypeScript"]
    F -->|"REST · idempotency · correlation ID"| A["FastAPI"]
    A --> P[("PostgreSQL 16 + pgvector")]
    A --> R[("Redis 7")]
    A --> O["Provider orchestrator"]
    O -->|"optional live"| L["Anthropic"]
    O -->|"default local"| M["Deterministic mock"]
    O -->|"final degradation"| B["Rule-based fallback"]
    X["Prometheus"] -->|scrape| A
    G["Grafana"] -->|query| X
    T["Toxiproxy"] -->|fault injection| M
```

![Architecture and SLO page](docs/images/architecture-slo.png)

The detailed request path and trust boundaries are documented in [docs/architecture.md](docs/architecture.md).

## Reliability design

| Control | Behaviour |
| --- | --- |
| Timeout | Each provider attempt defaults to 12 seconds and all attempts share a 15-second total budget |
| Retry | SDK retries are disabled; the application makes at most three operations for connection errors, 429, and 5xx, with budgeted backoff |
| Circuit breaker | Opens after five consecutive failures, probes after 60 seconds, closes on probe success |
| Structured output | Pydantic validates every provider response; malformed JSON gets one correction attempt and evidence must map to incident input |
| Fallback | Rule-based result is labelled and always sets `requires_human_escalation=true` |
| Cache | Redis key covers normalized input, runbook versions, provider, and model; 15-minute TTL |
| Rate limit | Redis-backed, 10 analysis requests per client per minute by default |
| Idempotency | Active same-payload replay precedes rate limiting; payload drift returns 409 and expired keys can be reused |
| Correlation | Safe request IDs appear in response headers, JSON logs, and request metrics |
| Input safety | 64 KiB body limit, field constraints, production CORS allowlist, sensitive log redaction |

## SLO targets

These are targets, not achieved uptime claims.

- Valid `POST /analyse` requests: **≥99.5% monthly success**; user-caused 4xx responses excluded.
- p95 analysis latency: **<3 seconds in mock mode** and **<12 seconds in live mode**, measured separately.
- When the primary provider fails: **≥95% successful fallback**.

The [SLO](docs/slo.md) and [error-budget policy](docs/error-budget.md) define indicators, burn rates, and release gates.

## Measured evaluation

`make eval` produces two distinct reports from checked-in synthetic data. The numbers below were generated on 5 August 2026 and were not entered by hand.

| Evaluation | Cases | Severity | Recall@1 | Recall@3 | JSON boundary | Escalation | Average processing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic regression | 60 | 100% | 100% | 100% | 100% | 100% | 0.305 ms in-memory |
| End-to-end HTTP mock | 12 | 100% | 100% | 100% | 100% | 100% | 10.871 ms end-to-end |

The regression run is in-memory: it uses no HTTP provider or database and makes no production or generalisation claim. The end-to-end run uses perturbed held-out cases through `AnalysisService`, PostgreSQL/pgvector, Redis, Toxiproxy, and the actual HTTP mock-provider adapter; it recorded 12 provider requests, zero cache hits, and zero fallbacks. See the generated [evaluation summary](reports/evaluation/latest.md), [regression report](reports/evaluation/regression-latest.md), and [end-to-end report](reports/evaluation/end-to-end-latest.md). Live Anthropic was not run because no API key was configured and paid-provider use was outside this validation.

## Load and chaos results

The following measurements came from the local Apple Silicon Docker Compose stack on 5 August 2026. They describe controlled synthetic runs, not production capacity, availability, or achieved uptime.

| Five-minute configured load mode | Cold provider path | Warm cache path |
| --- | ---: | ---: |
| Concurrent users | 20 | 20 |
| Locust CSV requests | 9,419 | 9,593 |
| Failures | 0 | 0 |
| Locust throughput | 15.40 req/s | 32.01 req/s |
| p50 / p95 / p99 HTTP latency | 27 / 62 / 100 ms | 15 / 29 / 46 ms |
| Cache hits / misses | 0 / 9,449 | 9,538 / 61 |
| Cache-hit rate | 0% | 99.3645% |
| Provider requests / fallbacks | 9,449 / 0 | 61 / 0 |
| Observed wall clock | 613.474 s | 300.676 s |

Cold gives every request a unique safe nonce and idempotency key, so it exercises the HTTP mock-provider path. Warm clears Redis and then repeats the fixed 60-fixture set. During the cold run the local host or Docker scheduler paused, extending the observed wall clock beyond the configured 300 seconds; the unadjusted Locust throughput is retained rather than normalised. Locust CSV and Prometheus can differ slightly because metrics include requests still in flight when the CSV writer closes. See the [comparison](reports/loadtests/comparison.md), [cold report](reports/loadtests/cold/latest.md), [warm report](reports/loadtests/warm/latest.md), and archived [9,700-request baseline](reports/loadtests/baseline-2026-08-05/latest.md).

| 15,000 ms provider-latency chaos | Before total budget | After total budget |
| --- | ---: | ---: |
| Request duration | 36.446 s | 15.080 s |
| Returned provider | `rule-based-fallback` | `rule-based-fallback` |
| Requires human escalation | Yes | Yes |
| Fallback counter delta | +1 | +1 |
| Retry-attempt counter delta | Not exported | +1 |
| Toxic cleanup verified | Yes | Yes, empty toxic list |

The new run stayed within the 16-second assertion around the 15-second total provider budget. The original report remains unchanged in [baseline-2026-08-05](reports/chaos/baseline-2026-08-05/latest.md); the current [chaos report](reports/chaos/latest.md), [JSON](reports/chaos/latest.json), and [postmortem](docs/postmortems/001-provider-timeout.md) document the before/after evidence. One successful experiment does not establish the 95% fallback SLO.

### Grafana screenshot

The dashboard is provisioned from [incident-copilot.json](observability/grafana/dashboards/incident-copilot.json) with request rate, success rate, p50/p95, provider errors, fallback rate, cache hit rate, circuit state, and severity distribution.

![Provisioned Grafana dashboard after load and chaos experiments](docs/images/grafana-dashboard.png)

## Run locally

Requirements: Docker Desktop with Compose v2 and GNU Make. All selected images publish ARM64-compatible builds for Apple Silicon.

```bash
git clone https://github.com/enzheShen/reliable-ai-incident-copilot.git
cd reliable-ai-incident-copilot
make bootstrap
make dev
```

`make bootstrap` creates an ignored `.env` from `.env.example`, builds images, applies Alembic migrations, and seeds 12 runbooks plus 60 synthetic incidents. Default mock mode does not need an API key.

| Service | URL |
| --- | --- |
| React application | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Stop the stack with `make stop`.

## Configuration

Copy `.env.example` to the ignored `.env` file. Important settings include:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_MODE` | `mock` | Selects deterministic mock or optional live mode |
| `ANTHROPIC_API_KEY` | empty | Optional paid-provider credential; never commit it |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | Live provider model |
| `LLM_TIMEOUT_SECONDS` | `12` | Per-attempt provider deadline |
| `LLM_TOTAL_TIMEOUT_SECONDS` | `15` | Total provider-operation budget, including retry waits |
| `CACHE_TTL_SECONDS` | `900` | Assessment cache lifetime |
| `RATE_LIMIT_PER_MINUTE` | `10` | Per-client analysis limit |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Consecutive failures before opening |
| `CIRCUIT_BREAKER_RECOVERY_SECONDS` | `60` | Open interval before a half-open probe |
| `CORS_ORIGINS` | `http://localhost:5173` | Explicit browser origin allowlist |

## Development commands

```text
make bootstrap     build, migrate, and seed
make dev           start the full local stack
make stop          stop the stack
make test          backend and frontend tests
make lint          Ruff and ESLint
make typecheck     mypy and TypeScript
make eval          regression and end-to-end mock evaluation reports
make load-test-cold 20-user, five-minute provider-path report
make load-test-warm 20-user, five-minute cache-path report
make load-test     run cold then warm and generate a comparison
make chaos-demo    Toxiproxy fallback experiment and report
make seed          idempotently seed fixed data
make migrate       apply Alembic migrations
make clean         stop services and remove local caches
```

## API example

```bash
curl -sS http://localhost:8000/api/v1/incidents/analyse \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-api-latency-1' \
  -d '{
    "service_name": "orders-api",
    "environment": "production",
    "started_at": "2026-08-05T10:30:00Z",
    "symptoms": "p95 latency exceeds 2.4 seconds",
    "logs": ["slow request route=/orders duration=2480ms"],
    "metrics": {"p95_latency_ms": 2480, "error_rate": 0.08},
    "recent_changes": ["release 1.4.2"],
    "reporter": "synthetic-monitor"
  }'
```

The full API is available in Swagger. History responses use `{page, page_size, total, items}` and support `service`, `severity`, and `status` filters.

## Testing

`make test` passes 59 backend tests against real PostgreSQL/pgvector and Redis plus 11 frontend tests. GitHub Actions configures pgvector and Redis services so integration tests execute rather than skip.

Tests verify fields and state transitions, not just status codes. The contract suite compares Pydantic fields with the TypeScript interfaces to catch undetected response drift. CI never invokes Anthropic.

## Limitations

- This version has no authentication, tenancy, or field-level encryption and must use synthetic data.
- The in-process circuit breaker is per backend process; a multi-replica deployment would require shared breaker state or coordinated routing.
- Deterministic hashing retrieval is reproducible but not a semantic embedding model.
- No monthly traffic history exists, so the SLOs remain targets; one local load run cannot establish availability.
- Load and chaos results are single-machine experiments and should not be interpreted as production capacity.
- The cold run experienced a local wall-clock pause, so its unadjusted throughput is retained with that limitation.
- There is no public deployment yet. **Live demo: not deployed.**

## Future work

- Add authentication and tenant-aware retention before accepting real incident data.
- Compare a locally hosted embedding model against deterministic retrieval on a larger evaluation set.
- Export OpenTelemetry traces and correlate provider spans with assessment IDs.
- Run scheduled load and chaos experiments in a stable CI environment.
- Add a public deployment only after cost, privacy, and abuse controls are approved.

## Documentation

- [Testing strategy](docs/testing-strategy.md)
- [Threat model](docs/threat-model.md)
- [Operator runbook](docs/runbook.md)
- [Error-budget policy](docs/error-budget.md)

MIT licensed. See [LICENSE](LICENSE).
