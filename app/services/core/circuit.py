from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Implementa resiliência contra falhas dos processadores"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        name: str = "circuit_breaker",
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.name = name
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() - self.last_failure_time > timedelta(
            seconds=self.timeout_seconds
        )

    def _on_success(self) -> None:
        """Handle successful call"""
        self.failure_count = 0
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN and self.success_count >= 3:
            self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    @property
    def is_healthy(self) -> bool:
        """Check if circuit breaker is allowing calls"""
        return self.state != CircuitState.OPEN
