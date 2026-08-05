from __future__ import annotations

import json

import anthropic
from pydantic import ValidationError

from app.providers.base import Provider, ProviderError
from app.providers.prompt import SYSTEM_PROMPT
from app.repositories import RunbookMatch
from app.schemas import IncidentCreate, ProviderAssessment


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.model = model
        self.client = client or anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    async def assess(
        self,
        incident: IncidentCreate,
        runbooks: list[RunbookMatch],
        prompt: str,
    ) -> ProviderAssessment:
        del incident, runbooks
        last_error: Exception | None = None
        current_prompt = prompt
        for attempt in range(2):
            try:
                message = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1_500,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": current_prompt}],
                )
                text_parts = [getattr(block, "text", "") for block in message.content]
                payload = json.loads("".join(text_parts))
                return ProviderAssessment.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                current_prompt = (
                    f"{prompt}\nYour previous output was invalid. Return valid JSON only."
                )
                if attempt == 0:
                    continue
            except anthropic.APIStatusError as exc:
                raise ProviderError(
                    "Anthropic provider returned an HTTP error", status_code=exc.status_code
                ) from exc
            except anthropic.APIConnectionError as exc:
                raise ProviderError("Anthropic provider connection failed", retryable=True) from exc
        raise ProviderError(
            "Anthropic provider returned invalid structured output", retryable=False
        ) from last_error
