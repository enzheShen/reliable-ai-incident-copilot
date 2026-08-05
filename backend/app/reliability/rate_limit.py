from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class RedisRateLimitClient(Protocol):
    async def incr(self, name: str) -> int: ...

    async def expire(self, name: str, time: int) -> object: ...


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(self, client: RedisRateLimitClient, limit: int) -> None:
        self.client = client
        self.limit = limit

    async def check(self, client_id: str, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        bucket = current.strftime("%Y%m%d%H%M")
        key = f"rate-limit:analyse:{client_id}:{bucket}"
        count = await self.client.incr(key)
        if count == 1:
            await self.client.expire(key, 61)
        if count > self.limit:
            raise RateLimitExceeded
        return self.limit - count
