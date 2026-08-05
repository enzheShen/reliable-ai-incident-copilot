# Cold load-test report

Generated at `2026-08-05T18:30:56.345636+00:00` with 20 users for 5m. This was the unique synthetic incidents exercising the HTTP mock-provider path.

| Metric | Result |
| --- | ---: |
| Requests | 9419 |
| Observed wall clock | 613.474 seconds |
| Failures | 0 |
| Error rate | 0.0 |
| Throughput | 15.395880281754003 req/s |
| p50 HTTP latency | 27.0 ms |
| p95 HTTP latency | 62.0 ms |
| p99 HTTP latency | 100.0 ms |
| Cache hits | 0 |
| Cache misses | 9449 |
| Cache hit rate | 0.0 |
| Provider requests | 9449 |
| Fallbacks | 0 |

## Scope

The test ran on local Docker Desktop with checked-in synthetic data. It is not a production capacity or achieved-uptime measurement. Throughput is Locust's unadjusted wall-clock value; a longer observed wall clock records local host or Docker scheduling pauses rather than hiding them.
