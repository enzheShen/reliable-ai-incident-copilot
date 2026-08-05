from __future__ import annotations

from typing import Protocol

from app.schemas import ProviderAssessment


class RedisCacheClient(Protocol):
    async def get(self, name: str) -> str | None: ...

    async def set(self, name: str, value: str, *, ex: int) -> object: ...


class AssessmentCache:
    def __init__(self, client: RedisCacheClient, ttl_seconds: int) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> ProviderAssessment | None:
        value = await self.client.get(key)
        if value is None:
            return None
        return ProviderAssessment.model_validate_json(value)

    async def set(self, key: str, assessment: ProviderAssessment) -> None:
        await self.client.set(key, assessment.model_dump_json(), ex=self.ttl_seconds)
