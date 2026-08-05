# Provider latency chaos report

Status: **passed**

Injected latency: **15000 ms**

Fallback metric: **0.0 → 1.0**

Provider used: **rule-based-fallback**

## Timeline

- `2026-08-05T16:49:22.853255+00:00` — Removed existing provider toxics
- `2026-08-05T16:49:24.900231+00:00` — Backend and mock provider confirmed healthy
- `2026-08-05T16:49:24.905678+00:00` — Injected downstream provider latency
- `2026-08-05T16:50:01.352393+00:00` — Timeout and retry path returned validated rule-based fallback
- `2026-08-05T16:50:01.355601+00:00` — Prometheus fallback counter increase verified
- `2026-08-05T16:50:01.366017+00:00` — Toxics removed and dependency health restored

## Evidence

```json
{
  "incident_id": "633d243d-0457-445a-934d-69a09acb6ff6",
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
  "processing_time_ms": 36410,
  "created_at": "2026-08-05T16:49:24.915654Z",
  "cache_hit": false
}
```
