from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_random_exponential
from tenacity.wait import wait_base

from app.providers import ProviderError

T = TypeVar("T")


def is_retryable_provider_error(exception: BaseException) -> bool:
    return isinstance(exception, ProviderError) and exception.transient


async def call_provider_with_retry(
    operation: Callable[[], Awaitable[T]],
    timeout_seconds: float,
    *,
    wait: wait_base | None = None,
) -> T:
    retrying = AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait or wait_random_exponential(multiplier=0.25, max=2.0),
        retry=retry_if_exception(is_retryable_provider_error),
        reraise=True,
    )
    async for attempt in retrying:
        with attempt:
            try:
                async with asyncio.timeout(timeout_seconds):
                    return await operation()
            except TimeoutError as exc:
                raise ProviderError("Provider request timed out", retryable=True) from exc
    raise RuntimeError("Retry loop ended without a result")
