from datetime import UTC, datetime

import pytest

from app.reliability import RateLimiter, RateLimitExceeded


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, name: str) -> int:
        self.counts[name] = self.counts.get(name, 0) + 1
        return self.counts[name]

    async def expire(self, name: str, time: int) -> object:
        self.expirations[name] = time
        return True


@pytest.mark.asyncio
async def test_rate_limiter_allows_limit_then_rejects() -> None:
    redis = FakeRedis()
    limiter = RateLimiter(redis, limit=2)
    now = datetime(2026, 8, 5, 12, 30, tzinfo=UTC)
    assert await limiter.check("client", now) == 1
    assert await limiter.check("client", now) == 0
    with pytest.raises(RateLimitExceeded):
        await limiter.check("client", now)
    assert next(iter(redis.expirations.values())) == 61
