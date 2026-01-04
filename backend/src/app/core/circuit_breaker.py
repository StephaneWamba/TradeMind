"""Circuit breaker pattern for resilience against external service failures."""

from enum import Enum
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Awaitable, Any, Optional, Dict
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2,
        name: str = "circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                # Timeout expired, try half-open
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(
                    "Circuit breaker entering HALF_OPEN state", name=self.name)
            else:
                # Still in timeout period
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN. "
                    f"Last failure: {self.last_failure_time}"
                )

        # Attempt to call function
        try:
            result = await func(*args, **kwargs)

            # Success - reset counters
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(
                        "Circuit breaker CLOSED after recovery", name=self.name)
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

            return result

        except Exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker OPENED",
                    name=self.name,
                    failure_count=self.failure_count,
                    error=str(e)
                )

            # In half-open, any failure closes it again
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                logger.warning(
                    "Circuit breaker re-OPENED in half-open state", name=self.name)

            raise

    def reset(self):
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset", name=self.name)

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
