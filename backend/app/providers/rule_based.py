from __future__ import annotations

from app.providers.base import Provider
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment, Severity

SEVERITY_BY_RUNBOOK = {
    "api-latency-spike": Severity.SEV2,
    "database-connection-saturation": Severity.SEV1,
    "redis-outage": Severity.SEV2,
    "authentication-failure": Severity.SEV1,
    "rate-limit-spike": Severity.SEV3,
    "upstream-dependency-timeout": Severity.SEV2,
    "memory-leak": Severity.SEV2,
    "cpu-saturation": Severity.SEV2,
    "disk-capacity-exhaustion": Severity.SEV1,
    "message-queue-backlog": Severity.SEV2,
    "tls-certificate-expiry": Severity.SEV1,
    "deployment-regression": Severity.SEV2,
}


def deterministic_assessment(
    incident: IncidentCreate, runbooks: list[RunbookMatch], *, fallback: bool
) -> ProviderAssessment:
    primary = runbooks[0] if runbooks else None
    severity = SEVERITY_BY_RUNBOOK.get(primary.slug if primary else "", Severity.SEV3)
    evidence = list(incident.logs[:3])
    evidence.extend(f"{key}={value:g}" for key, value in sorted(incident.metrics.items())[:4])
    if not evidence:
        evidence.append(incident.symptoms[:500])
    cause = primary.title if primary else "Cause could not be mapped to a known runbook"
    actions = (
        [part.strip() for part in primary.content.split(".") if part.strip()][:3]
        if primary
        else ["Preserve evidence and assign a human incident owner"]
    )
    return ProviderAssessment(
        severity=severity,
        summary=f"{incident.service_name}: {incident.symptoms[:700]}",
        likely_causes=[cause],
        evidence=evidence,
        recommended_actions=actions,
        confidence=0.58 if fallback else 0.9,
        requires_human_escalation=True if fallback else severity in {Severity.SEV1, Severity.SEV2},
    )


class RuleBasedFallbackProvider(Provider):
    name = "rule-based-fallback"
    model = "rules-v1"

    async def assess(
        self,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        del prompt
        return deterministic_assessment(incident, runbooks, fallback=True)
