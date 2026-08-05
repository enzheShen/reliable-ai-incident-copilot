from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, ReliabilityEvent
from app.schemas import LatencyPoint, ReliabilityEventResponse, ReliabilitySummary


def percentile(values: list[int], percentile_value: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(percentile_value * len(ordered)) - 1)
    return ordered[index]


class ReliabilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, window_minutes: int = 60) -> ReliabilitySummary:
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)
        assessments = list(
            (
                await self.session.execute(
                    select(
                        Assessment.created_at,
                        Assessment.processing_time_ms,
                        Assessment.severity,
                        Assessment.fallback_used,
                    ).where(Assessment.created_at >= since)
                )
            ).tuples()
        )
        events = list(
            (
                await self.session.execute(
                    select(ReliabilityEvent.event_type).where(ReliabilityEvent.created_at >= since)
                )
            ).scalars()
        )
        latencies = [row[1] for row in assessments]
        failures = events.count("analysis_failure")
        completed = len(assessments)
        buckets: dict[str, list[int]] = defaultdict(list)
        for created_at, processing_time_ms, _, _ in assessments:
            bucket_minute = created_at.minute - created_at.minute % 5
            label = created_at.replace(minute=bucket_minute, second=0, microsecond=0).strftime(
                "%H:%M"
            )
            buckets[label].append(processing_time_ms)
        cache_hits = events.count("cache_hit")
        cache_misses = events.count("cache_miss")
        cache_total = cache_hits + cache_misses
        severity_counts = Counter(row[2] for row in assessments)
        return ReliabilitySummary(
            window_minutes=window_minutes,
            request_count=completed + failures,
            success_rate=completed / (completed + failures) if completed + failures else 1.0,
            p50_latency_ms=percentile(latencies, 0.5),
            p95_latency_ms=percentile(latencies, 0.95),
            fallback_count=len([row for row in assessments if row[3]]),
            cache_hit_rate=cache_hits / cache_total if cache_total else 0.0,
            provider_failure_count=events.count("provider_failure"),
            severity_distribution={
                key: severity_counts.get(key, 0) for key in ("SEV1", "SEV2", "SEV3", "SEV4")
            },
            latency_series=[
                LatencyPoint(
                    time=label,
                    p50=percentile(values, 0.5),
                    p95=percentile(values, 0.95),
                )
                for label, values in sorted(buckets.items())
            ],
        )

    async def events(self, limit: int = 50) -> list[ReliabilityEventResponse]:
        statement = (
            select(ReliabilityEvent).order_by(ReliabilityEvent.created_at.desc()).limit(limit)
        )
        records = list((await self.session.execute(statement)).scalars())
        return [
            ReliabilityEventResponse(
                id=item.id,
                event_type=item.event_type,
                provider=item.provider,
                details=item.details,
                created_at=item.created_at,
            )
            for item in records
        ]
