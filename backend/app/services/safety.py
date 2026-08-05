from __future__ import annotations

import re

from app.providers import ProviderError
from app.schemas import IncidentCreate, ProviderAssessment, Severity

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
IGNORED_TOKENS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def _normalized(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(value.casefold()))


def _tokens(value: str) -> set[str]:
    return set(_normalized(value).split()) - IGNORED_TOKENS


def incident_evidence_sources(incident: IncidentCreate) -> list[str]:
    sources = [incident.symptoms, *incident.logs, *incident.recent_changes]
    for key, value in incident.metrics.items():
        sources.extend((key, f"{key}={value:g}", f"{key} {value:g}"))
    return [source for source in sources if source.strip()]


def evidence_is_grounded(evidence: str, sources: list[str]) -> bool:
    normalized_evidence = _normalized(evidence)
    evidence_tokens = _tokens(evidence)
    if not normalized_evidence or not evidence_tokens:
        return False
    for source in sources:
        normalized_source = _normalized(source)
        if normalized_evidence in normalized_source or normalized_source in normalized_evidence:
            return True
        overlap = evidence_tokens & _tokens(source)
        required = 1 if len(evidence_tokens) == 1 else 2
        if len(overlap) >= required and len(overlap) / len(evidence_tokens) >= 0.5:
            return True
    return False


def apply_provider_safety_policy(
    incident: IncidentCreate,
    assessment: ProviderAssessment,
    *,
    fallback: bool = False,
) -> ProviderAssessment:
    sources = incident_evidence_sources(incident)
    if not all(evidence_is_grounded(item, sources) for item in assessment.evidence):
        raise ProviderError("Provider evidence was not grounded in incident input", retryable=False)
    requires_escalation = (
        fallback
        or assessment.severity in {Severity.SEV1, Severity.SEV2}
        or assessment.confidence < 0.70
        or assessment.requires_human_escalation
    )
    return assessment.model_copy(
        update={"requires_human_escalation": requires_escalation}
    )
