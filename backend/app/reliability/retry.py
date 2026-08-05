from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TypeVar

from app.providers import ProviderError

T = TypeVar("T")
AttemptObserver = Callable[[int, float, BaseException | None], None]
RetryDelay = Callable[[int], float]


class ProviderBudgetExceeded(ProviderError):
    def __init__(self) -> None:
        super().__init__("Provider total time budget exhausted", retryable=False)


def is_retryable_provider_error(exception: BaseException) -> bool:
    return isinstance(exception, ProviderError) and exception.transient


async def call_provider_with_retry(
    operation: Callable[[], Awaitable[T]],
    attempt_timeout_seconds: float,
    *,
    total_timeout_seconds: float | None = None,
    retry_delay: RetryDelay | None = None,
    on_attempt: AttemptObserver | None = None,
    max_attempts: int = 3,
) -> T:
    total_timeout = total_timeout_seconds or attempt_timeout_seconds * max_attempts
    delay_for = retry_delay or (
        lambda attempt: random.uniform(0.0, min(2.0, 0.25 * (2 ** (attempt - 1))))  # noqa: S311
    )
    loop = asyncio.get_running_loop()
    deadline = loop.time() + total_timeout

    for attempt_number in range(1, max_attempts + 1):
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise ProviderBudgetExceeded()
        timeout = min(attempt_timeout_seconds, remaining)
        started = perf_counter()
        error: BaseException | None = None
        try:
            async with asyncio.timeout(timeout):
                result = await operation()
        except TimeoutError as exc:
            error = ProviderError("Provider request timed out", retryable=True)
            error.__cause__ = exc
        except Exception as exc:
            error = exc
        else:
            if on_attempt:
                on_attempt(attempt_number, perf_counter() - started, None)
            return result

        if on_attempt:
            on_attempt(attempt_number, perf_counter() - started, error)
        if not is_retryable_provider_error(error) or attempt_number >= max_attempts:
            raise error

        delay = max(0.0, delay_for(attempt_number))
        remaining = deadline - loop.time()
        if remaining <= delay:
            raise ProviderBudgetExceeded() from error
        await asyncio.sleep(delay)

    raise RuntimeError("Provider retry loop ended without a result")
