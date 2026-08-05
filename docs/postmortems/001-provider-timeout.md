# Postmortem 001: provider timeout

## Summary

On 5 August 2026, a controlled Toxiproxy experiment added 15,000 ms of latency to
the deterministic mock provider. The backend exhausted its 12-second per-attempt
deadline and two retries, then returned a schema-valid rule-based fallback. The
experiment passed all automated assertions and restored the dependency afterward.

## Impact

- One synthetic analysis request took 36.446 seconds.
- The request completed with HTTP 200 and `fallback_used=true`.
- The fallback required human escalation and cited three retrieved runbooks.
- No real users, production data, or external services were involved.
- The 36.446-second response does not meet the project's mock p95 target; this was a
  deliberate failure-path experiment, not part of the normal load measurement.

## Timeline

All timestamps are UTC and were written automatically by `make chaos-demo`.

- `16:49:22.853` — Existing Toxiproxy toxics removed.
- `16:49:24.900` — Backend and mock provider confirmed healthy.
- `16:49:24.905` — 15,000 ms provider latency injected.
- `16:50:01.352` — Timeout and retry path returned the validated fallback.
- `16:50:01.355` — Prometheus fallback counter increase verified.
- `16:50:01.366` — Toxic removed and dependency health restored.

## Detection

The chaos runner detected the condition through the request deadline and then
asserted the response contract, fallback provider, escalation flag, Prometheus
counter delta, and post-cleanup health checks.

## Root cause

The injected 15-second latency exceeded the configured 12-second timeout for each
provider attempt. Because provider timeouts are retryable, the initial attempt and
two permitted retries consumed approximately 36 seconds before the final fallback
ran. The experiment intentionally created this condition; it was not an organic
provider incident.

## What worked

- Provider output never bypassed Pydantic validation.
- The final result clearly identified `rule-based-fallback` and required escalation.
- The relevant `Upstream dependency timeout` runbook ranked first.
- `llm_fallback_total` increased from 0 to 1.
- Cleanup removed the toxic and both backend and mock-provider health recovered.

## What did not work

- Per-attempt deadlines allowed retries to extend total user-visible latency to
  36.446 seconds.
- The response contract does not currently expose retry count or the individual
  attempt durations, so the report infers the retry sequence from configuration and
  total duration.

## Corrective actions

| Action | Owner | Status |
| --- | --- | --- |
| Add an end-to-end provider time budget and stop retries when insufficient budget remains | Backend maintainer | Planned |
| Export retry-attempt count and per-attempt duration metrics | Observability maintainer | Planned |
| Add a shorter timeout chaos case to CI while retaining the full local demo | Platform maintainer | Proposed |
| Re-run the experiment after deadline budgeting and compare total fallback latency | Reliability maintainer | Pending |

## Evidence

- [`reports/chaos/latest.json`](../../reports/chaos/latest.json) contains the
  machine-written timestamps, response, latency, and counter values.
- [`reports/chaos/latest.md`](../../reports/chaos/latest.md) is the generated readable
  experiment report.
- The assessment ID was `633d243d-0457-445a-934d-69a09acb6ff6`.

## Follow-up owners/status

No corrective action is marked complete in this portfolio run. Ownership labels
describe the project role responsible for the next iteration; they do not imply a
staffed production team.
