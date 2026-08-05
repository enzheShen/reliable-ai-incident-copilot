from __future__ import annotations

from abc import ABC, abstractmethod

from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable

    @property
    def transient(self) -> bool:
        if self.retryable is not None:
            return self.retryable
        return self.status_code == 429 or (self.status_code is not None and self.status_code >= 500)


class Provider(ABC):
    name: str
    model: str

    @abstractmethod
    async def assess(
        self,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        raise NotImplementedError
