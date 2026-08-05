from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Assessment, AssessmentRunbook, Incident
from app.schemas import IncidentCreate, IncidentStatus, Severity


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: IncidentCreate) -> Incident:
        incident = Incident(**payload.model_dump(mode="python"))
        self.session.add(incident)
        await self.session.flush()
        return incident

    async def get(self, incident_id: UUID) -> Incident | None:
        statement = (
            select(Incident)
            .where(Incident.id == incident_id)
            .options(
                selectinload(Incident.assessment)
                .selectinload(Assessment.runbook_links)
                .selectinload(AssessmentRunbook.runbook)
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        service: str | None,
        severity: Severity | None,
        status: IncidentStatus | None,
    ) -> tuple[int, list[tuple[Incident, Assessment | None]]]:
        conditions = []
        if service:
            conditions.append(Incident.service_name == service)
        if severity:
            conditions.append(Assessment.severity == severity.value)
        if status == IncidentStatus.ASSESSED:
            conditions.append(Assessment.id.is_not(None))
        elif status == IncidentStatus.PENDING:
            conditions.append(Assessment.id.is_(None))

        base: Select[tuple[Incident, Assessment]] = select(Incident, Assessment).outerjoin(
            Assessment, Assessment.incident_id == Incident.id
        )
        count_statement = select(func.count(Incident.id)).outerjoin(
            Assessment, Assessment.incident_id == Incident.id
        )
        if conditions:
            base = base.where(*conditions)
            count_statement = count_statement.where(*conditions)
        base = (
            base.order_by(Incident.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = int(await self.session.scalar(count_statement) or 0)
        rows = cast(
            list[tuple[Incident, Assessment | None]],
            list((await self.session.execute(base)).tuples().all()),
        )
        return total, rows
