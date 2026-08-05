from __future__ import annotations

import logging

from app.database import async_session_factory
from app.models import ReliabilityEvent
from app.observability.metrics import ANALYSIS_FAILURES

logger = logging.getLogger(__name__)


async def record_analysis_failure(error: BaseException, stage: str) -> None:
    ANALYSIS_FAILURES.inc()
    details = {"error_type": type(error).__name__, "stage": stage}
    try:
        async with async_session_factory() as session:
            session.add(
                ReliabilityEvent(
                    event_type="analysis_failure",
                    provider=None,
                    details=details,
                )
            )
            await session.commit()
    except Exception as reporting_error:
        logger.warning(
            "analysis failure event could not be persisted",
            extra={
                "event": "analysis_failure_reporting_error",
                "error_type": type(reporting_error).__name__,
                "stage": "failure_reporting",
            },
        )
