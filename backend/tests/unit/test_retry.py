import pytest
from tenacity import wait_none

from app.providers import ProviderError
from app.reliability import call_provider_with_retry, is_retryable_provider_error


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

    assert await call_provider_with_retry(operation, 1, wait=wait_none()) == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_non_retryable_failure_is_not_retried() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ProviderError("authentication", status_code=401)

    with pytest.raises(ProviderError):
        await call_provider_with_retry(operation, 1, wait=wait_none())
    assert attempts == 1
