# Postmortem 001: provider timeout budget

## Summary

On 5 August 2026, two controlled Toxiproxy experiments added 15,000 ms of latency to the deterministic mock provider. The original implementation applied a 12-second timeout independently to the initial operation and two retries, returning a validated fallback after 36.446 seconds. After adding a 15-second total provider budget, the same experiment returned the fallback in 15.080 seconds.

Both runs used synthetic data and local Docker services. No real user, production system, paid provider, or public deployment was involved.

## Impact

- Baseline: one synthetic request took 36.446 seconds before fallback.
- Corrected run: one synthetic request took 15.080 seconds and passed the 16-second chaos assertion.
- Both responses used `rule-based-fallback` and required human escalation.
- The current run increased `llm_fallback_total` by one and `provider_retry_attempts_total` by one.
- Cleanup removed the latency toxic and verified an empty toxic list plus healthy dependencies.

The baseline latency did not meet the mock p95 target. Neither controlled request represents production traffic or establishes the fallback SLO.

## Detection and evidence

The runner asserts the response contract, fallback provider, escalation flag, monotonic request duration, Prometheus counter deltas, toxic removal, and restored health. The original machine-written files remain unchanged under [`reports/chaos/baseline-2026-08-05`](../../reports/chaos/baseline-2026-08-05/latest.json). The corrected run is in [`reports/chaos/latest.json`](../../reports/chaos/latest.json).

The host UTC clock changed during the corrected run, so its wall-clock timeline is not suitable for calculating duration. The runner uses `time.monotonic()` for the 15.080-second budget assertion; both timestamp and monotonic evidence are retained rather than rewritten.

## Root cause

The original retry loop had no shared end-to-end deadline. A 15-second injected response exceeded the 12-second attempt timeout three times, so retries extended user-visible latency to 36.446 seconds. The Anthropic SDK also retained its own default retries, which could multiply live-mode HTTP attempts beneath the application retry loop.

## Corrective implementation

- Anthropic `AsyncAnthropic` now sets `max_retries=0`.
- The application remains the only retry owner and performs at most three operations.
- `LLM_TOTAL_TIMEOUT_SECONDS` defaults to 15 seconds and includes operation time and retry waits.
- Each operation receives `min(LLM_TIMEOUT_SECONDS, remaining total budget)`.
- Prometheus exports retry-operation count and per-attempt duration without a retry-count label.
- The chaos runner fails nonzero for experiment or cleanup failure and verifies the toxic list is empty.

## Before and after

| Evidence | Baseline | Corrected run |
| --- | ---: | ---: |
| Injected latency | 15,000 ms | 15,000 ms |
| Request duration | 36.446 s | 15.080 s |
| Application retry metric | Not exported | +1 |
| Fallback metric | +1 | +1 |
| Fallback provider | `rule-based-fallback` | `rule-based-fallback` |
| Human escalation | Required | Required |
| Cleanup | Health restored | Empty toxic list and health restored |

## Corrective actions

| Action | Status |
| --- | --- |
| Add and test a total provider budget | Completed |
| Disable nested Anthropic SDK retries | Completed |
| Export retry-attempt and attempt-duration metrics | Completed |
| Make cleanup/report failure propagate a nonzero exit | Completed |
| Re-run the full 15,000 ms experiment and retain baseline evidence | Completed |
| Run recurring chaos in a stable CI environment | Not implemented |

No individual or production team ownership is implied by this portfolio exercise.
