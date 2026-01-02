"""
Circuit Breaker pattern for protecting against cascading failures.

Prevents repeated calls to a failing API, allowing it time to recover.
Essential for 24/7 operation with vnstock's limited API.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
from loguru import logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "state_changes": self.state_changes,
            "success_rate": round(
                self.successful_calls / max(self.total_calls, 1) * 100, 2
            ),
        }


class CircuitBreaker:
    """
    Circuit Breaker for vnstock API protection.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Service failing, all requests rejected immediately
    - HALF_OPEN: Testing if service recovered with limited requests
    
    Transitions:
    - CLOSED -> OPEN: When failure count reaches threshold
    - OPEN -> HALF_OPEN: After recovery timeout
    - HALF_OPEN -> CLOSED: On successful test request
    - HALF_OPEN -> OPEN: On failed test request
    """
    
    def __init__(
        self,
        name: str = "vnstock",
        failure_threshold: int = 5,
        recovery_timeout: int = 300,  # 5 minutes
        half_open_max_calls: int = 1,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for logging
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Test calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        self.stats = CircuitBreakerStats()
        
        logger.info(
            f"🔌 CircuitBreaker '{name}' initialized: "
            f"threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN
    
    async def _should_allow_request(self) -> bool:
        """
        Check if a request should be allowed.
        
        Returns: True if request should proceed
        """
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return True
            
            # Still open, reject
            self.stats.rejected_calls += 1
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            # Allow limited test calls
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            
            # Too many test calls, reject
            self.stats.rejected_calls += 1
            return False
        
        return False
    
    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self.stats.state_changes += 1
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
        
        logger.info(
            f"🔌 CircuitBreaker '{self.name}': "
            f"{old_state.value} -> {new_state.value}"
        )
    
    async def record_success(self):
        """Record a successful call."""
        async with self._lock:
            self.stats.successful_calls += 1
            self.stats.last_success_time = time.monotonic()
            
            if self._state == CircuitState.HALF_OPEN:
                # Service recovered, close circuit
                await self._transition_to(CircuitState.CLOSED)
            
            # Reset failure count on success
            self._failure_count = 0
    
    async def record_failure(self):
        """Record a failed call."""
        async with self._lock:
            self.stats.failed_calls += 1
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self.stats.last_failure_time = self._last_failure_time
            
            if self._state == CircuitState.HALF_OPEN:
                # Test failed, reopen circuit
                await self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self.failure_threshold:
                # Threshold reached, open circuit
                await self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"⚠️ CircuitBreaker '{self.name}' OPEN: "
                    f"{self._failure_count} consecutive failures"
                )
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Function arguments
            
        Returns: Function result
        
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If function fails
        """
        async with self._lock:
            if not await self._should_allow_request():
                raise CircuitOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable, retry after {self.recovery_timeout}s"
                )
        
        self.stats.total_calls += 1
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self.record_success()
            return result
            
        except Exception as e:
            await self.record_failure()
            raise
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "stats": self.stats.to_dict(),
        }
    
    async def force_close(self):
        """Force close the circuit (for manual recovery)."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            logger.info(f"🔌 CircuitBreaker '{self.name}' manually closed")
    
    async def force_open(self):
        """Force open the circuit (for maintenance)."""
        async with self._lock:
            await self._transition_to(CircuitState.OPEN)
            self._last_failure_time = time.monotonic()
            logger.info(f"🔌 CircuitBreaker '{self.name}' manually opened")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Decorator for easy circuit breaker protection
def circuit_protected(circuit_breaker: CircuitBreaker):
    """
    Decorator to protect a function with a circuit breaker.
    
    Usage:
        @circuit_protected(my_circuit_breaker)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.execute(func, *args, **kwargs)
        return wrapper
    return decorator


# Global circuit breaker instance
_global_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 300,
    reset: bool = False
) -> CircuitBreaker:
    """
    Get or create the global circuit breaker instance.
    """
    global _global_circuit_breaker
    
    if _global_circuit_breaker is None or reset:
        _global_circuit_breaker = CircuitBreaker(
            name="vnstock",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    
    return _global_circuit_breaker
