import pytest

from app.reliability import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_opens_half_opens_and_closes() -> None:
    current_time = [100.0]
    transitions: list[tuple[CircuitState, CircuitState]] = []

    async def record(previous: CircuitState, current: CircuitState) -> None:
        transitions.append((previous, current))

    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_seconds=60,
        clock=lambda: current_time[0],
        on_transition=record,
    )
    for _ in range(5):
        await breaker.before_call()
        await breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await breaker.before_call()

    current_time[0] += 60
    await breaker.before_call()
    assert breaker.state is CircuitState.HALF_OPEN
    await breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    assert transitions == [
        (CircuitState.CLOSED, CircuitState.OPEN),
        (CircuitState.OPEN, CircuitState.HALF_OPEN),
        (CircuitState.HALF_OPEN, CircuitState.CLOSED),
    ]


@pytest.mark.asyncio
async def test_failed_half_open_probe_reopens_circuit() -> None:
    current_time = [0.0]
    breaker = CircuitBreaker(1, 60, clock=lambda: current_time[0])
    await breaker.before_call()
    await breaker.record_failure()
    current_time[0] = 61
    await breaker.before_call()
    await breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    assert breaker.opened_at == 61
