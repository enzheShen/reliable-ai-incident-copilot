# Provider latency chaos report

Status: **passed**

Injected latency: **15000 ms**

Request duration: **15.08 seconds** (limit: 16.0 seconds)

Fallback metric: **0.0 → 1.0**

Retry-attempt metric: **0.0 → 1.0**

Provider used: **rule-based-fallback**

Toxic cleanup verified: **True**

## Timeline

- `2026-08-05T18:34:06.483385+00:00` — Removed existing provider toxics
- `2026-08-05T18:34:07.522006+00:00` — Backend and mock provider confirmed healthy
- `2026-08-05T18:34:07.531659+00:00` — Injected downstream provider latency
- `2026-08-05T18:49:22.413464+00:00` — Total-budget retry path returned validated rule-based fallback
- `2026-08-05T18:49:22.420449+00:00` — Prometheus fallback and retry-attempt counter increases verified
- `2026-08-05T18:49:22.431682+00:00` — Toxics removed and dependency health restored

## Evidence

```json
{
  "incident_id": "45bebbe9-0e82-40f4-b976-ada29a75eb28",
  "severity": "SEV2",
  "summary": "chaos-demo-api: The mock upstream dependency exceeds its response deadline.",
  "likely_causes": [
    "Upstream dependency timeout"
  ],
  "evidence": [
    "upstream gateway timeout deadline exceeded",
    "error_rate=0.4",
    "upstream_p95_ms=15000"
  ],
  "recommended_actions": [
    "Measure upstream latency and timeout rates by operation",
    "Confirm client deadlines and retry amplification",
    "Open the circuit or use a safe fallback, reduce nonessential calls, and contact the dependency owner with correlation IDs and measured windows"
  ],
  "runbook_references": [
    {
      "id": "00000000-0000-4000-8000-000000000006",
      "title": "Upstream dependency timeout",
      "relevance": 0.48349381934087954
    },
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "title": "API latency spike",
      "relevance": 0.32232920295981193
    },
    {
      "id": "00000000-0000-4000-8000-000000000005",
      "title": "Rate-limit spike",
      "relevance": 0.08703882992267609
    }
  ],
  "confidence": 0.58,
  "requires_human_escalation": true,
  "provider_used": "rule-based-fallback",
  "fallback_used": true,
  "processing_time_ms": 15020,
  "created_at": "2026-08-05T18:34:07.542677Z",
  "cache_hit": false
}
```
