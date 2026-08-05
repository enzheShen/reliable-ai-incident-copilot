from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories import ReliabilityRepository
from app.schemas import ReliabilityEventResponse, ReliabilitySummary

router = APIRouter(prefix="/reliability", tags=["reliability"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/summary", response_model=ReliabilitySummary)
async def reliability_summary(
    session: SessionDependency,
    window_minutes: Annotated[int, Query(ge=5, le=10_080)] = 60,
) -> ReliabilitySummary:
    return await ReliabilityRepository(session).summary(window_minutes)


@router.get("/events", response_model=list[ReliabilityEventResponse])
async def reliability_events(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    window_minutes: Annotated[int, Query(ge=5, le=10_080)] = 60,
) -> list[ReliabilityEventResponse]:
    return await ReliabilityRepository(session).events(limit, window_minutes)
