# Public Demo Deployment Plan

## Goal

Publish a truthful, lightweight portfolio demo of Reliable AI Incident Copilot without a custom domain, a paid AI provider, or a time-limited database. The deployment demonstrates build, release, persistence, health checks, and public accessibility; it does not claim production readiness, enterprise use, achieved uptime, or real incident data.

## Scope and non-goals

### Included

- One public Render web service containing the built React SPA and FastAPI API.
- One free Render Key Value instance for cache, rate limiting, circuit state, and idempotency support.
- One free Neon PostgreSQL database with the `vector` extension for durable application data.
- Automatic deployment from the GitHub `main` branch after CI passes.
- Idempotent schema migration and synthetic seed data at service start.
- Same-origin frontend/API traffic, avoiding cross-origin deployment complexity.
- Public health, API documentation, demo analysis, history, and reliability pages.
- Existing input limits, rate limiting, safe deterministic analysis, and synthetic data disclosures.

### Excluded

- Anthropic or any other paid model in the public deployment.
- Render's 30-day free PostgreSQL database.
- Custom domains, payment cards, paid instances, persistent disks, multiple replicas, Kubernetes, or public Grafana.
- Claims of production traffic, real customers, real incidents, an uptime SLA, or enterprise capacity.

## Architecture

```text
Browser
  |
  | HTTPS, same origin
  v
Render free web service
  |- React static build
  |- FastAPI /api/v1
  |- /health/live, /health/ready, /metrics, /docs
  |
  |-- TLS --> Neon free PostgreSQL + pgvector (durable)
  `-- private Redis URL --> Render free Key Value (ephemeral cache)
```

The frontend is compiled into the backend image and served by FastAPI. This removes the need for a separate frontend account or public CORS configuration and keeps the public demo to one URL.

## Runtime behavior

- `LLM_MODE=rules` uses the deterministic rule-based provider as the primary provider. It produces useful synthetic demo output without an external model, a secret, a timeout penalty, or billable usage.
- The existing Anthropic adapter remains in the repository for optional private evaluation but is not enabled in the public service.
- The database URL accepts a standard Neon `postgresql://` connection string and is normalized to SQLAlchemy's Psycopg 3 dialect at startup.
- Startup applies `alembic upgrade head`, then runs the idempotent seed command, then starts Uvicorn on Render's `PORT`.
- Uvicorn interprets the proxy headers supplied by Render's hosting edge so rate limiting uses the originating client address rather than the Render proxy address.
- React Router paths fall back to the SPA entry point without intercepting API, health, metrics, OpenAPI, or Swagger routes.

## Free resources

### Render

- Web service: `free` plan; may sleep after 15 minutes of inactivity and cold-start on the next request.
- Key Value: `free` plan with persistence disabled. Cache loss after a restart is acceptable because PostgreSQL remains the durable source of truth.
- Static frontend is bundled into the web service, so no second Render service is required.
- No payment method will be added. If a free monthly limit is reached, the service may pause instead of incurring an automatic charge.

### Neon

- PostgreSQL project: `free` plan with no trial-expiration dependency.
- `vector` is created by the existing Alembic migration.
- The connection string is stored only as a Render secret and is never committed.

## Environment variables

| Name | Source | Public value or rule |
|---|---|---|
| `APP_ENV` | Blueprint | `production` |
| `LOG_LEVEL` | Blueprint | `INFO` |
| `DATABASE_URL` | User-created Neon secret | Never committed |
| `REDIS_URL` | Render service reference | Internal connection string |
| `LLM_MODE` | Blueprint | `rules` |
| `CORS_ORIGINS` | Blueprint | Empty JSON list because traffic is same-origin |
| `RATE_LIMIT_PER_MINUTE` | Blueprint | Conservative public-demo limit |
| `MAX_INCIDENT_BODY_BYTES` | Blueprint | Existing 64 KiB limit |
| `DATA_DIR` | Image | `/app/data` |
| `REPORTS_DIR` | Image | `/app/reports` |

No API key is required for the public deployment.

## Release sequence

1. Complete local code and configuration changes.
2. Run backend lint, types, unit/integration tests, frontend lint/types/tests/build, and Docker builds.
3. Run the complete production image locally against PostgreSQL and Redis.
4. Confirm the repository contains no secret and the worktree diff is limited to deployment work.
5. Pause for the user to register Render and Neon with GitHub and confirm both free plans.
6. Create the Neon project and copy its direct (non-pooled) connection string into Render's secret field. Neon recommends a direct connection for ORM schema migrations.
7. Create the Render Blueprint from the repository and confirm every service is `Free` before applying.
8. Deploy only after the user confirms that no payment method or paid plan is selected.
9. Verify the public URL, readiness, Swagger, SPA routes, analysis flow, history, cold start, and persistence after a redeploy.
10. Add the verified URL and accurate deployment evidence to the README. Update résumé language only after the URL passes validation.

## Rollback and failure handling

- Code rollback: redeploy the previous known-good Git commit.
- Service rollback: Render retains recent deploys; no DNS or domain change is involved.
- Database rollback: the first deployment uses the existing additive initial migration. No destructive migration is introduced.
- Cache failure: the application reports readiness failure; cache contents may be discarded and recreated.
- Deployment failure: keep the GitHub repository and local Docker workflow unchanged; do not upgrade to a paid plan as a workaround.
- Cost or policy change: remove the public service or migrate to another free provider. The Docker image and externalized configuration keep the application portable.

## Acceptance criteria

- All existing tests pass and new deployment-path tests cover rule mode, URL normalization, SPA routing, and startup configuration.
- The production Docker image serves the frontend and API from one origin.
- `/health/live` returns `200`; `/health/ready` confirms PostgreSQL and Redis.
- A synthetic example produces an assessment without calling a paid provider.
- The created incident appears in history and remains after a backend redeploy.
- No secret, payment method, paid plan, or time-limited Render PostgreSQL database is used.
- README wording says `public demo` and `synthetic data`, not `production system` or `real users`.
