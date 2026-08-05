# Testing strategy

The test pyramid separates deterministic logic from infrastructure behaviour and browser-facing contracts.

- Backend unit tests cover finite schemas, canonical hashes, cache keys, prompt construction, evidence grounding, structured output, Anthropic error mapping without network access, total retry budgets, circuit-breaker transitions, fallback selection, log redaction, and chaos cleanup failure.
- Integration tests run against PostgreSQL/pgvector and Redis for migrations, repositories, rate limiting, caching, idempotency, readiness, analysis, and history pagination.
- Contract tests validate API payloads against shared TypeScript/Pydantic fixtures to detect field drift.
- Frontend tests use Vitest and React Testing Library for validation, loading, success, fallback, error, reliability empty/error/success states, architecture rendering, and history pagination/detail visibility.
- The deterministic regression evaluation measures a real JSON serialization boundary but remains in-memory. A separate end-to-end mock evaluation covers PostgreSQL/pgvector, Redis, Toxiproxy, and HTTP-provider integration on 12 perturbed synthetic cases.
- Cold and warm Locust modes record HTTP latency alongside Prometheus cache, provider, and fallback deltas. Toxiproxy provides controlled dependency-failure evidence and fails the command if cleanup cannot be verified.

CI never calls a paid provider. Live-provider tests skip clearly when no key is configured.
