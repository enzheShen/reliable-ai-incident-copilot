import pytest

from app.providers import ProviderError
from app.reliability import (
    ProviderBudgetExceeded,
    call_provider_with_retry,
    is_retryable_provider_error,
)


def test_retry_policy_classifies_only_transient_failures() -> None:
    assert is_retryable_provider_error(ProviderError("limited", status_code=429))
    assert is_retryable_provider_error(ProviderError("server", status_code=503))
    assert is_retryable_provider_error(ProviderError("connection", retryable=True))
    assert not is_retryable_provider_error(ProviderError("auth", status_code=401))
    assert not is_retryable_provider_error(ProviderError("validation", status_code=422))


@pytest.mark.asyncio
async def test_transient_failure_retries_twice_then_succeeds() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderError("temporary", status_code=503)
        return "ok"

    assert await call_provider_with_retry(operation, 1, retry_delay=lambda _: 0) == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_non_retryable_failure_is_not_retried() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ProviderError("authentication", status_code=401)

    with pytest.raises(ProviderError):
        await call_provider_with_retry(operation, 1, retry_delay=lambda _: 0)
    assert attempts == 1


@pytest.mark.asyncio
async def test_total_budget_stops_retries_and_caps_attempt_timeout() -> None:
    import asyncio

    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(0.2)
        return "late"

    with pytest.raises(ProviderBudgetExceeded):
        await call_provider_with_retry(
            operation,
            0.08,
            total_timeout_seconds=0.12,
            retry_delay=lambda _: 0,
        )
    assert attempts == 2


@pytest.mark.asyncio
async def test_application_never_executes_more_than_three_operations() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ProviderError("temporary", status_code=429)

    with pytest.raises(ProviderError):
        await call_provider_with_retry(
            operation,
            1,
            total_timeout_seconds=5,
            retry_delay=lambda _: 0,
        )
    assert attempts == 3
