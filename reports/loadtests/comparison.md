# Cold and warm load-test comparison

| Mode | Requests | Failures | req/s | p50 ms | p95 ms | p99 ms | Cache-hit rate | Provider requests | Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cold | 9419 | 0 | 15.395880281754003 | 27.0 | 62.0 | 100.0 | 0.0 | 9449 | 0 |
| warm | 9593 | 0 | 32.01290197349641 | 15.0 | 29.0 | 46.0 | 0.993645 | 61 | 0 |

Cold uses a unique synthetic reporter and idempotency key for every request, while warm repeats the fixed 60-fixture dataset after clearing Redis. These local Docker measurements are separate path-specific evidence, not production capacity or achieved uptime.
