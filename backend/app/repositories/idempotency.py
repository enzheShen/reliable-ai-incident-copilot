from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> IdempotencyKey | None:
        statement = select(IdempotencyKey).where(IdempotencyKey.key == key).with_for_update()
        result = await self.session.execute(statement)
        record = result.scalar_one_or_none()
        if record is not None and record.expires_at <= datetime.now(UTC):
            await self.session.delete(record)
            await self.session.flush()
            return None
        return record

    async def create(
        self,
        *,
        key: str,
        payload_hash: str,
        incident_id: UUID,
        ttl_seconds: int,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            key=key,
            request_hash=payload_hash,
            incident_id=incident_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        self.session.add(record)
        await self.session.flush()
        return record
