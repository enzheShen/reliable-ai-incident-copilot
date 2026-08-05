# Threat model

## Assets

Provider credentials, incident content, assessment history, service availability, and operational metrics are the protected assets.

## Principal risks and controls

| Risk | Control |
| --- | --- |
| Credential disclosure | Environment-only secrets, ignored `.env`, redacted structured logs, CI secret scan |
| Oversized or abusive requests | 64 KiB body limit, field length constraints, Redis rate limit |
| Prompt injection in logs | Treat incident text as data, fixed provider instructions, strict output schema |
| Duplicate writes | Idempotency key plus canonical request hash and database constraint |
| Cross-origin misuse | Explicit environment-specific CORS allowlist; wildcard rejected in production |
| Provider outage or malformed output | Timeout, narrow retry policy, circuit breaker, one parse retry, explicit fallback |
| Sensitive persistence | Synthetic fixtures only; no authorization or cookie values in events/logs |
| Dependency compromise | Pinned container/runtime versions and automated dependency/secret checks |

## Out of scope for version one

User authentication, tenant isolation, encrypted field-level storage, and public internet deployment are not claimed. They are prerequisites before handling real operational data.
