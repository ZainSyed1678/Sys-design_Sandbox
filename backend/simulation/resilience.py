import math
import random
from enum import Enum
from typing import Dict, Any, Optional

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Standard three-state Circuit Breaker (Closed, Open, Half-Open).
    Protects downstream dependencies from cascading collapse.
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 5.0,
        half_open_probes: int = 2,
        success_threshold: int = 2,
    ):
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = max(0.01, float(recovery_timeout))
        self.half_open_probes = max(1, int(half_open_probes))
        self.success_threshold = max(1, int(success_threshold))

        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.active_probes: int = 0
        self.last_state_change: float = 0.0

        # Metrics
        self.trip_count: int = 0
        self.rejected_requests: int = 0

    def allow_request(self, current_time: float) -> bool:
        """Determines whether a request can be dispatched downstream."""
        if self.state == CircuitState.CLOSED:
            return True

        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed to transition to HALF_OPEN
            if current_time - self.last_state_change >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = current_time
                self.active_probes = 1
                self.consecutive_successes = 0
                return True
            else:
                self.rejected_requests += 1
                return False

        elif self.state == CircuitState.HALF_OPEN:
            # Allow up to half_open_probes in flight
            if self.active_probes < self.half_open_probes:
                self.active_probes += 1
                return True
            else:
                self.rejected_requests += 1
                return False

        return False

    def record_success(self, current_time: float):
        """Records a successful response from the downstream dependency."""
        if self.state == CircuitState.HALF_OPEN:
            self.active_probes = max(0, self.active_probes - 1)
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.success_threshold:
                # Fully recovered: close the circuit
                self.state = CircuitState.CLOSED
                self.last_state_change = current_time
                self.consecutive_failures = 0
                self.consecutive_successes = 0
                self.active_probes = 0
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self, current_time: float):
        """Records a failed or timed-out request."""
        if self.state == CircuitState.CLOSED:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                # Trip to OPEN
                self.state = CircuitState.OPEN
                self.last_state_change = current_time
                self.trip_count += 1
                self.consecutive_failures = 0
                self.consecutive_successes = 0
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately trips back to OPEN
            self.state = CircuitState.OPEN
            self.last_state_change = current_time
            self.trip_count += 1
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.active_probes = 0

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "trip_count": self.trip_count,
            "rejected_requests": self.rejected_requests,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


class TokenBucket:
    """
    Token Bucket rate limiter / load shedder.
    Refills at refill_rate tokens/sec up to capacity.
    """
    def __init__(self, capacity: float = 100.0, refill_rate: float = 50.0):
        self.capacity = max(1.0, float(capacity))
        self.refill_rate = max(0.1, float(refill_rate))
        self.tokens: float = self.capacity
        self.last_refill_time: float = 0.0
        self.rejected_count: int = 0
        self.accepted_count: int = 0

    def allow_request(self, current_time: float, cost: float = 1.0) -> bool:
        """Attempt to consume tokens. Returns True if accepted, False if shed."""
        dt = max(0.0, current_time - self.last_refill_time)
        self.tokens = min(self.capacity, self.tokens + (dt * self.refill_rate))
        self.last_refill_time = current_time

        if self.tokens >= cost:
            self.tokens -= cost
            self.accepted_count += 1
            return True
        else:
            self.rejected_count += 1
            return False

    def get_state(self) -> Dict[str, Any]:
        return {
            "tokens": round(self.tokens, 2),
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
        }


class RetryPolicy:
    """
    Retry configuration with fixed/exponential backoff, seeded jitter, and retry budget.
    """
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        backoff_type: str = "exponential",
        max_delay: float = 5.0,
        jitter: bool = True,
        retry_budget_ratio: Optional[float] = None,  # e.g. 0.2 means max 20% retries
    ):
        self.max_retries = max(0, int(max_retries))
        self.base_delay = max(0.001, float(base_delay))
        self.backoff_type = backoff_type.lower()
        self.max_delay = max(self.base_delay, float(max_delay))
        self.jitter = bool(jitter)
        self.retry_budget_ratio = float(retry_budget_ratio) if retry_budget_ratio is not None else None

        self.initial_attempts: int = 0
        self.retry_attempts: int = 0
        self.budget_exhausted_count: int = 0

    def can_retry(self, attempt: int) -> bool:
        """Check if attempt is within max_retries and conforms to retry budget."""
        if attempt > self.max_retries:
            return False

        if self.retry_budget_ratio is not None and self.initial_attempts > 0:
            allowed_retries = self.initial_attempts * self.retry_budget_ratio
            if self.retry_attempts >= allowed_retries:
                self.budget_exhausted_count += 1
                return False

        return True

    def calculate_delay(self, attempt: int, rng: random.Random) -> float:
        """Compute backoff delay with seeded jitter."""
        if self.backoff_type == "fixed":
            delay = self.base_delay
        else:
            # Full exponential backoff: base_delay * 2^(attempt - 1)
            exp_factor = 2.0 ** max(0, attempt - 1)
            delay = min(self.max_delay, self.base_delay * exp_factor)

        if self.jitter:
            # Full jitter: uniform random in [0, delay]
            return rng.uniform(0.0, delay)
        return delay

    def record_initial(self):
        self.initial_attempts += 1

    def record_retry(self):
        self.retry_attempts += 1

    def get_state(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "backoff_type": self.backoff_type,
            "initial_attempts": self.initial_attempts,
            "retry_attempts": self.retry_attempts,
            "budget_exhausted": self.budget_exhausted_count,
        }
