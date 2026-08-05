from __future__ import annotations

# Markdown report templates intentionally keep table rows and prose paragraphs intact.
# ruff: noqa: E501
import asyncio
import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.database import async_session_factory
from app.providers import deterministic_assessment
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment
from app.services.analysis import PROVIDER_CIRCUITS, AnalysisService
from app.services.embeddings import (
    cosine_similarity,
    deterministic_embedding,
    runbook_embedding,
)
from app.services.safety import apply_provider_safety_policy


def percentage(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def load_jsonl(path: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def validate_serialized_output(assessment: ProviderAssessment) -> bool:
    """Validate after crossing a JSON text boundary, not the existing model instance."""
    try:
        decoded = json.loads(assessment.model_dump_json())
        ProviderAssessment.model_validate(decoded)
    except (TypeError, ValueError):
        return False
    return True


def live_anthropic_status(settings: Settings) -> dict[str, str]:
    if not settings.anthropic_api_key:
        return {"status": "skipped", "reason": "ANTHROPIC_API_KEY is not configured"}
    return {
        "status": "not_run",
        "reason": "Live evaluation requires explicit paid-provider approval",
    }


def regression_evaluate() -> dict[str, Any]:
    settings = get_settings()
    runbook_records: list[dict[str, Any]] = json.loads(
        (settings.data_dir / "runbooks/runbooks.json").read_text(encoding="utf-8")
    )
    cases = load_jsonl(settings.data_dir / "evaluation/evaluation.jsonl")
    vectors = {
        record["id"]: runbook_embedding(record["title"], record["keywords"])
        for record in runbook_records
    }
    by_id = {record["id"]: record for record in runbook_records}
    severity_hits = 0
    recall_one_hits = 0
    recall_three_hits = 0
    valid_outputs = 0
    escalation_hits = 0
    processing_times: list[float] = []

    for case in cases:
        started = perf_counter()
        incident = IncidentCreate.model_validate(case["incident_input"])
        query = AnalysisService.retrieval_query(incident)
        query_vector = deterministic_embedding(query)
        ranked_ids = sorted(
            vectors,
            key=lambda runbook_id: cosine_similarity(query_vector, vectors[runbook_id]),
            reverse=True,
        )
        matches = [
            RunbookMatch(
                id=UUID(runbook_id),
                slug=by_id[runbook_id]["slug"],
                title=by_id[runbook_id]["title"],
                content=by_id[runbook_id]["content"],
                version=1,
                relevance=max(0.0, cosine_similarity(query_vector, vectors[runbook_id])),
            )
            for runbook_id in ranked_ids[:3]
        ]
        assessment = apply_provider_safety_policy(
            incident, deterministic_assessment(incident, matches, fallback=False)
        )
        valid_outputs += int(validate_serialized_output(assessment))
        severity_hits += int(assessment.severity.value == case["expected_severity"])
        recall_one_hits += int(ranked_ids[0] == case["expected_runbook"])
        recall_three_hits += int(case["expected_runbook"] in ranked_ids[:3])
        escalation_hits += int(
            assessment.requires_human_escalation == case["escalation_expected"]
        )
        processing_times.append((perf_counter() - started) * 1000)

    count = len(cases)
    return {
        "evaluation_type": "deterministic-regression",
        "execution": "in-memory",
        "http_provider_used": False,
        "database_used": False,
        "dataset": "checked-in synthetic regression cases",
        "cases": count,
        "severity_accuracy": percentage(severity_hits, count),
        "runbook_recall_at_1": percentage(recall_one_hits, count),
        "runbook_recall_at_3": percentage(recall_three_hits, count),
        "serialized_output_validation_rate": percentage(valid_outputs, count),
        "escalation_accuracy": percentage(escalation_hits, count),
        "average_in_memory_processing_time_ms": round(sum(processing_times) / count, 3),
        "live_anthropic": live_anthropic_status(settings),
        "limitations": [
            "No HTTP provider or database is used in this regression evaluation.",
            "Timing is in-memory evaluation processing time, not API or provider latency.",
            "These deterministic synthetic cases do not support a production or generalisation claim.",
        ],
    }


async def end_to_end_mock_evaluate() -> dict[str, Any]:
    settings = get_settings()
    cases = load_jsonl(settings.data_dir / "evaluation/held-out.jsonl")
    severity_hits = 0
    recall_one_hits = 0
    recall_three_hits = 0
    valid_outputs = 0
    escalation_hits = 0
    cache_hits = 0
    fallback_count = 0
    provider_requests = 0
    processing_times: list[float] = []
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    PROVIDER_CIRCUITS.clear()

    try:
        await redis.flushdb()
        async with async_session_factory() as session:
            service = AnalysisService(session, redis, settings=settings)
            for case in cases:
                incident = IncidentCreate.model_validate(case["incident_input"])
                started = perf_counter()
                outcome = await service.analyse(incident)
                processing_times.append((perf_counter() - started) * 1000)
                ranked_ids = [str(runbook.id) for runbook in outcome.runbooks]
                severity_hits += int(
                    outcome.assessment.severity.value == case["expected_severity"]
                )
                recall_one_hits += int(bool(ranked_ids) and ranked_ids[0] == case["expected_runbook"])
                recall_three_hits += int(case["expected_runbook"] in ranked_ids[:3])
                valid_outputs += int(validate_serialized_output(outcome.assessment))
                escalation_hits += int(
                    outcome.assessment.requires_human_escalation
                    == case["escalation_expected"]
                )
                cache_hits += int(outcome.cache_hit)
                fallback_count += int(outcome.fallback_used)
                provider_requests += int(not outcome.cache_hit and not outcome.fallback_used)
            await session.rollback()
    finally:
        await redis.aclose()

    count = len(cases)
    return {
        "evaluation_type": "end-to-end-mock",
        "execution": "AnalysisService",
        "http_provider_used": True,
        "provider": "deterministic-mock/mock-v1 via Toxiproxy",
        "database_used": True,
        "database_features": ["PostgreSQL", "pgvector runbook retrieval"],
        "dataset": "checked-in held-out perturbed synthetic cases",
        "cases": count,
        "severity_accuracy": percentage(severity_hits, count),
        "runbook_recall_at_1": percentage(recall_one_hits, count),
        "runbook_recall_at_3": percentage(recall_three_hits, count),
        "serialized_output_validation_rate": percentage(valid_outputs, count),
        "escalation_accuracy": percentage(escalation_hits, count),
        "average_end_to_end_processing_time_ms": round(sum(processing_times) / count, 3),
        "provider_request_count": provider_requests,
        "cache_hit_count": cache_hits,
        "fallback_count": fallback_count,
        "live_anthropic": live_anthropic_status(settings),
        "limitations": [
            "The provider is deterministic and local; live Anthropic was not called.",
            "The held-out data is synthetic and intentionally small.",
            "Local Docker results do not establish production performance or generalisation.",
        ],
    }


def regression_markdown(result: dict[str, Any]) -> str:
    return f"""# Deterministic regression evaluation

Generated by `python -m app.evaluation` from {result["cases"]} checked-in synthetic cases.

| Metric | Result |
| --- | ---: |
| Severity accuracy | {result["severity_accuracy"]} |
| Runbook recall@1 | {result["runbook_recall_at_1"]} |
| Runbook recall@3 | {result["runbook_recall_at_3"]} |
| Serialized output validation rate | {result["serialized_output_validation_rate"]} |
| Escalation accuracy | {result["escalation_accuracy"]} |
| Average in-memory processing time | {result["average_in_memory_processing_time_ms"]} ms |

## Scope

This is an **in-memory deterministic regression evaluation**. It uses no HTTP provider and no database. The JSON metric crosses a real serialize/parse/validate boundary, but it does not measure an external provider. Timing is in-memory processing time, not API or provider latency. These synthetic cases do not support a production or generalisation claim.

Live Anthropic evaluation: **{result["live_anthropic"]["status"]}** — {result["live_anthropic"]["reason"]}.
"""


def end_to_end_markdown(result: dict[str, Any]) -> str:
    return f"""# End-to-end mock evaluation

Generated by `python -m app.evaluation` from {result["cases"]} held-out, perturbed synthetic cases.

| Metric | Result |
| --- | ---: |
| Severity accuracy | {result["severity_accuracy"]} |
| Runbook recall@1 | {result["runbook_recall_at_1"]} |
| Runbook recall@3 | {result["runbook_recall_at_3"]} |
| Serialized HTTP output validation rate | {result["serialized_output_validation_rate"]} |
| Escalation accuracy | {result["escalation_accuracy"]} |
| Average end-to-end processing time | {result["average_end_to_end_processing_time_ms"]} ms |
| HTTP mock provider requests | {result["provider_request_count"]} |
| Cache hits | {result["cache_hit_count"]} |
| Fallbacks | {result["fallback_count"]} |

## Scope

This evaluation runs through `AnalysisService`, PostgreSQL/pgvector retrieval, Redis, Toxiproxy, and the actual HTTP mock-provider adapter. It uses only checked-in synthetic data. Live Anthropic was not called, and local deterministic results do not establish production performance or generalisation.
"""


def combined_markdown(result: dict[str, Any]) -> str:
    regression = result["regression"]
    end_to_end = result["end_to_end_mock"]
    return f"""# Evaluation summary

Generated at {result["generated_at"]}.

| Evaluation | Cases | Severity accuracy | Recall@1 | Recall@3 | Output validation | Escalation accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic regression (in-memory) | {regression["cases"]} | {regression["severity_accuracy"]} | {regression["runbook_recall_at_1"]} | {regression["runbook_recall_at_3"]} | {regression["serialized_output_validation_rate"]} | {regression["escalation_accuracy"]} |
| End-to-end HTTP mock | {end_to_end["cases"]} | {end_to_end["severity_accuracy"]} | {end_to_end["runbook_recall_at_1"]} | {end_to_end["runbook_recall_at_3"]} | {end_to_end["serialized_output_validation_rate"]} | {end_to_end["escalation_accuracy"]} |

The regression result is a fast in-memory guard. The end-to-end result exercises PostgreSQL/pgvector, Redis, Toxiproxy, and the HTTP mock-provider adapter. Neither result is a production/generalisation claim, and live Anthropic was not run.
"""


async def async_main() -> None:
    regression = regression_evaluate()
    end_to_end = await end_to_end_mock_evaluate()
    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "regression": regression,
        "end_to_end_mock": end_to_end,
    }
    output_dir = get_settings().reports_dir / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "regression-latest.json": json.dumps(regression, indent=2) + "\n",
        "regression-latest.md": regression_markdown(regression),
        "end-to-end-latest.json": json.dumps(end_to_end, indent=2) + "\n",
        "end-to-end-latest.md": end_to_end_markdown(end_to_end),
        "latest.json": json.dumps(result, indent=2) + "\n",
        "latest.md": combined_markdown(result),
    }
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    print(json.dumps(result, indent=2))


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
