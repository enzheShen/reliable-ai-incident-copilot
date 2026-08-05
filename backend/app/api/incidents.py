from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import Assessment, AssessmentRunbook
from app.observability.metrics import INCIDENT_ASSESSMENTS
from app.redis_client import redis_client
from app.reliability import RateLimiter, RateLimitExceeded, request_hash
from app.repositories import IdempotencyRepository, IncidentRepository
from app.schemas import (
    IncidentAssessment,
    IncidentCreate,
    IncidentDetail,
    IncidentHistoryItem,
    IncidentPage,
    IncidentStatus,
    Severity,
)
from app.services.analysis import AnalysisService
from app.services.failure_reporting import record_analysis_failure
from app.services.presenters import assessment_schema, detail_schema, history_item_schema

router = APIRouter(prefix="/incidents", tags=["incidents"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
settings = get_settings()


@router.post("/analyse", response_model=IncidentAssessment)
async def analyse_incident(
    payload: IncidentCreate,
    request: Request,
    response: Response,
    session: SessionDependency,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=200)
    ] = None,
) -> IncidentAssessment:
    stage = "idempotency"
    try:
        payload_hash = request_hash(payload)
        idempotency = IdempotencyRepository(session)
        if idempotency_key:
            existing = await idempotency.get(idempotency_key)
            if existing:
                if existing.request_hash != payload_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key was already used for a different request",
                    )
                incident = await IncidentRepository(session).get(existing.incident_id)
                if incident is None or incident.assessment is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotent request is not yet complete",
                    )
                response.headers["X-Idempotent-Replay"] = "true"
                return assessment_schema(incident.assessment)

        stage = "rate_limit"
        client_id = request.client.host if request.client else "unknown"
        try:
            await RateLimiter(redis_client, settings.rate_limit_per_minute).check(client_id)
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            ) from exc
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter unavailable",
            ) from exc

        stage = "provider_analysis"
        outcome = await AnalysisService(session, redis_client).analyse(payload)
        stage = "persistence"
        incident_repository = IncidentRepository(session)
        incident = await incident_repository.create(payload)
        assessment = Assessment(
            incident_id=incident.id,
            severity=outcome.assessment.severity.value,
            summary=outcome.assessment.summary,
            likely_causes=outcome.assessment.likely_causes,
            evidence=outcome.assessment.evidence,
            recommended_actions=outcome.assessment.recommended_actions,
            confidence=outcome.assessment.confidence,
            requires_human_escalation=outcome.assessment.requires_human_escalation,
            provider_used=outcome.provider_used,
            fallback_used=outcome.fallback_used,
            processing_time_ms=outcome.processing_time_ms,
        )
        session.add(assessment)
        await session.flush()
        for runbook in outcome.runbooks:
            session.add(
                AssessmentRunbook(
                    assessment_id=assessment.id,
                    runbook_id=runbook.id,
                    relevance_score=runbook.relevance,
                )
            )
        if idempotency_key:
            await idempotency.create(
                key=idempotency_key,
                payload_hash=payload_hash,
                incident_id=incident.id,
                ttl_seconds=settings.idempotency_ttl_seconds,
            )
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent idempotent request conflict; retry the same key",
            ) from exc
        saved = await incident_repository.get(incident.id)
        if saved is None or saved.assessment is None:
            raise HTTPException(status_code=500, detail="Assessment persistence failed")
        result = assessment_schema(saved.assessment).model_copy(
            update={"cache_hit": outcome.cache_hit}
        )
        INCIDENT_ASSESSMENTS.labels(
            result.severity.value,
            result.provider_used,
            str(result.fallback_used).lower(),
        ).inc()
        response.headers["X-Cache"] = "HIT" if outcome.cache_hit else "MISS"
        return result
    except IntegrityError as exc:
        await session.rollback()
        if idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent idempotent request conflict; retry the same key",
            ) from exc
        await record_analysis_failure(exc, stage)
        raise
    except HTTPException as exc:
        if exc.status_code >= 500:
            await session.rollback()
            await record_analysis_failure(exc, stage)
        raise
    except Exception as exc:
        await session.rollback()
        await record_analysis_failure(exc, stage)
        raise


@router.get("", response_model=IncidentPage)
async def list_incidents(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    service: Annotated[str | None, Query(max_length=100)] = None,
    severity: Severity | None = None,
    status_filter: Annotated[IncidentStatus | None, Query(alias="status")] = None,
) -> IncidentPage:
    total, rows = await IncidentRepository(session).list(
        page=page,
        page_size=page_size,
        service=service,
        severity=severity,
        status=status_filter,
    )
    items: list[IncidentHistoryItem] = [history_item_schema(*row) for row in rows]
    return IncidentPage(page=page, page_size=page_size, total=total, items=items)


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(incident_id: UUID, session: SessionDependency) -> IncidentDetail:
    incident = await IncidentRepository(session).get(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return detail_schema(incident)
