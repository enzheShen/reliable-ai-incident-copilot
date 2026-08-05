# Testing strategy

The test pyramid separates deterministic logic from infrastructure behaviour and browser-facing contracts.

- Backend unit tests cover schemas, canonical hashes, cache keys, prompt construction, structured output, retry classification, circuit-breaker transitions, and fallback selection.
- Integration tests run against PostgreSQL/pgvector and Redis for migrations, repositories, rate limiting, caching, idempotency, readiness, analysis, and history pagination.
- Contract tests validate API payloads against shared TypeScript/Pydantic fixtures to detect field drift.
- Frontend tests use Vitest and React Testing Library for validation, loading, success, fallback, error, and history filtering states.
- Deterministic evaluation measures severity, retrieval, structure, escalation, and latency.
- Locust and Toxiproxy provide performance and controlled dependency-failure evidence.

CI never calls a paid provider. Live-provider tests skip clearly when no key is configured.
