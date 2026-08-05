from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    pass


TransitionCallback = Callable[[CircuitState, CircuitState], Awaitable[None]]


async def _noop_transition(_: CircuitState, __: CircuitState) -> None:
    return None


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_seconds: float = 60,
        *,
        clock: Callable[[], float] = time.monotonic,
        on_transition: TransitionCallback = _noop_transition,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self.on_transition = on_transition
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at: float | None = None
        self._half_open_in_flight = False
        self._lock = asyncio.Lock()

    async def before_call(self) -> None:
        transition: tuple[CircuitState, CircuitState] | None = None
        async with self._lock:
            if self.state == CircuitState.OPEN:
                assert self.opened_at is not None
                if self.clock() - self.opened_at < self.recovery_seconds:
                    raise CircuitOpenError("Provider circuit is open")
                previous = self.state
                self.state = CircuitState.HALF_OPEN
                self._half_open_in_flight = True
                transition = (previous, self.state)
            elif self.state == CircuitState.HALF_OPEN:
                if self._half_open_in_flight:
                    raise CircuitOpenError("Provider circuit half-open probe is in progress")
                self._half_open_in_flight = True
        if transition:
            await self.on_transition(*transition)

    async def record_success(self) -> None:
        transition: tuple[CircuitState, CircuitState] | None = None
        async with self._lock:
            previous = self.state
            self.failures = 0
            self.opened_at = None
            self._half_open_in_flight = False
            self.state = CircuitState.CLOSED
            if previous != self.state:
                transition = (previous, self.state)
        if transition:
            await self.on_transition(*transition)

    async def record_failure(self) -> None:
        transition: tuple[CircuitState, CircuitState] | None = None
        async with self._lock:
            previous = self.state
            self.failures += 1
            self._half_open_in_flight = False
            if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = self.clock()
            if previous != self.state:
                transition = (previous, self.state)
        if transition:
            await self.on_transition(*transition)
