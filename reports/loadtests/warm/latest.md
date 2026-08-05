# Warm load-test report

Generated at `2026-08-05T18:30:56.399379+00:00` with 20 users for 5m. This was the fixed 60-fixture set exercising the assessment-cache path after warm-up.

| Metric | Result |
| --- | ---: |
| Requests | 9593 |
| Observed wall clock | 300.676 seconds |
| Failures | 0 |
| Error rate | 0.0 |
| Throughput | 32.01290197349641 req/s |
| p50 HTTP latency | 15.0 ms |
| p95 HTTP latency | 29.0 ms |
| p99 HTTP latency | 46.0 ms |
| Cache hits | 9538 |
| Cache misses | 61 |
| Cache hit rate | 0.993645 |
| Provider requests | 61 |
| Fallbacks | 0 |

## Scope

The test ran on local Docker Desktop with checked-in synthetic data. It is not a production capacity or achieved-uptime measurement. Throughput is Locust's unadjusted wall-clock value; a longer observed wall clock records local host or Docker scheduling pauses rather than hiding them.
