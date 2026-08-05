# Evaluation summary

Generated at 2026-08-05T18:10:55.699320+00:00.

| Evaluation | Cases | Severity accuracy | Recall@1 | Recall@3 | Output validation | Escalation accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic regression (in-memory) | 60 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| End-to-end HTTP mock | 12 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

The regression result is a fast in-memory guard. The end-to-end result exercises PostgreSQL/pgvector, Redis, Toxiproxy, and the HTTP mock-provider adapter. Neither result is a production/generalisation claim, and live Anthropic was not run.
