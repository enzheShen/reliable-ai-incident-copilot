from app.models import Assessment, Incident
from app.schemas import (
    IncidentAssessment,
    IncidentCreate,
    IncidentDetail,
    IncidentHistoryItem,
    IncidentStatus,
    RunbookReference,
    Severity,
)


def assessment_schema(assessment: Assessment) -> IncidentAssessment:
    references = [
        RunbookReference(
            id=link.runbook.id,
            title=link.runbook.title,
            relevance=link.relevance_score,
        )
        for link in sorted(
            assessment.runbook_links, key=lambda item: item.relevance_score, reverse=True
        )
    ]
    return IncidentAssessment(
        incident_id=assessment.incident_id,
        severity=Severity(assessment.severity),
        summary=assessment.summary,
        likely_causes=assessment.likely_causes,
        evidence=assessment.evidence,
        recommended_actions=assessment.recommended_actions,
        runbook_references=references,
        confidence=assessment.confidence,
        requires_human_escalation=assessment.requires_human_escalation,
        provider_used=assessment.provider_used,
        fallback_used=assessment.fallback_used,
        processing_time_ms=assessment.processing_time_ms,
        created_at=assessment.created_at,
    )


def history_item_schema(incident: Incident, assessment: Assessment | None) -> IncidentHistoryItem:
    return IncidentHistoryItem(
        id=incident.id,
        service_name=incident.service_name,
        environment=incident.environment,
        started_at=incident.started_at,
        created_at=incident.created_at,
        status=IncidentStatus.ASSESSED if assessment else IncidentStatus.PENDING,
        severity=Severity(assessment.severity) if assessment else None,
        summary=assessment.summary if assessment else None,
    )


def detail_schema(incident: Incident) -> IncidentDetail:
    return IncidentDetail(
        id=incident.id,
        created_at=incident.created_at,
        incident=IncidentCreate(
            service_name=incident.service_name,
            environment=incident.environment,
            started_at=incident.started_at,
            symptoms=incident.symptoms,
            logs=incident.logs,
            metrics=incident.metrics,
            recent_changes=incident.recent_changes,
            reporter=incident.reporter,
        ),
        assessment=assessment_schema(incident.assessment) if incident.assessment else None,
    )
