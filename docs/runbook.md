# Operator runbook

## Start and verify

1. Copy `.env.example` to `.env` without adding a paid key unless live mode is intentionally being tested.
2. Run `make bootstrap`, then `make dev`.
3. Check `/health/live`, `/health/ready`, Prometheus targets, and the provisioned Grafana dashboard.

## Common failures

- **Readiness reports PostgreSQL unavailable:** inspect the database healthcheck, then run `make migrate`.
- **Redis unavailable:** analyses requiring rate limiting fail closed; restore Redis and check the readiness event.
- **Provider failures:** confirm the circuit state and fallback counters. Fallback assessments require human escalation by design.
- **Migration mismatch:** stop application writes, inspect Alembic current/head revisions, and apply only the checked-in migration.

## Recovery evidence

Record correlation IDs, health responses, relevant Prometheus counter deltas, and commands used. Never paste keys, authorization headers, cookies, or real user logs into an issue or postmortem.
