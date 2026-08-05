from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.providers.base import Provider, ProviderError
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment


class DeterministicMockProvider(Provider):
    name = "deterministic-mock"
    model = "mock-v1"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client

    async def assess(
        self,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        request = {
            "incident": incident.model_dump(mode="json"),
            "runbooks": [
                {
                    "id": str(runbook.id),
                    "slug": runbook.slug,
                    "title": runbook.title,
                    "content": runbook.content,
                    "relevance": runbook.relevance,
                }
                for runbook in runbooks
            ],
            "prompt_digest_input": prompt,
        }
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(f"{self.base_url}/v1/assess", json=request)
            response.raise_for_status()
            return ProviderAssessment.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                "Mock provider returned an HTTP error", status_code=exc.response.status_code
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError("Mock provider connection failed", retryable=True) from exc
        except (ValidationError, ValueError) as exc:
            raise ProviderError(
                "Mock provider returned invalid structured output", retryable=False
            ) from exc
        finally:
            if owns_client:
                await client.aclose()
