# Threat model

## Assets

Provider credentials, incident content, assessment history, service availability, and operational metrics are the protected assets.

## Principal risks and controls

| Risk | Control |
| --- | --- |
| Credential disclosure | Environment-only secrets, ignored `.env`, recursively redacted structured logs, and a limited CI check for sensitive filenames and Anthropic-key patterns |
| Oversized or abusive requests | 64 KiB body limit, field length constraints, Redis rate limit |
| Prompt injection in logs | Treat incident text as data, fixed provider instructions, strict output schema |
| Duplicate writes | Idempotency key plus canonical request hash and database constraint |
| Cross-origin misuse | Explicit environment-specific CORS allowlist; wildcard rejected in production |
| Provider outage or malformed output | Per-attempt and total budgets, SDK retries disabled, narrow application retry policy, circuit breaker, one parse correction, evidence grounding, explicit fallback |
| Sensitive persistence | Synthetic fixtures only; no authorization or cookie values in events/logs |
| Dependency drift | Pinned direct application and container versions; dependency auditing is not currently automated |

## Out of scope for version one

User authentication, tenant isolation, encrypted field-level storage, and public internet deployment are not claimed. They are prerequisites before handling real operational data.

The CI pattern check is deliberately narrow. It is not a complete secret scanner and does not replace history scanning, credential rotation, or a dedicated dependency audit. Only checked-in synthetic incident data is permitted in this version.
