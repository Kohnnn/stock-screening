"""
Advanced Rate Limiter for VnStock API calls.

Implements Token Bucket algorithm with exponential backoff for robust rate limiting.
Designed for 24/7 operation with vnstock's limited API calls.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class TokenBucket:
    """
    Token Bucket rate limiter for smooth API request distribution.
    
    Allows bursts up to capacity while maintaining average rate.
    Perfect for APIs with rate limits.
    """
    capacity: float  # Maximum tokens (burst capacity)
    refill_rate: float  # Tokens added per second
    tokens: float = field(default=None)
    last_refill: float = field(default=None)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    
    def __post_init__(self):
        if self.tokens is None:
            self.tokens = self.capacity
        if self.last_refill is None:
            self.last_refill = time.monotonic()
    
    async def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens, waiting if necessary.
        
        Returns: Wait time in seconds (0 if no wait needed)
        """
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Calculate wait time for required tokens
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            
            logger.debug(f"⏳ Rate limit: waiting {wait_time:.2f}s for {tokens_needed:.1f} tokens")
            await asyncio.sleep(wait_time)
            
            # Refill and consume
            await self._refill()
            self.tokens -= tokens
            
            return wait_time
    
    async def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without waiting.
        
        Returns: True if tokens acquired, False otherwise
        """
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        return self.tokens


@dataclass
class ExponentialBackoff:
    """
    Exponential backoff strategy for handling API failures.
    
    Automatically increases delay after each failure,
    resets after success.
    """
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 300.0  # Maximum delay (5 minutes)
    multiplier: float = 2.0  # Delay multiplier after each failure
    jitter: float = 0.1  # Random jitter factor (0.1 = ±10%)
    
    _current_delay: float = field(default=None, repr=False)
    _failure_count: int = field(default=0, repr=False)
    
    def __post_init__(self):
        if self._current_delay is None:
            self._current_delay = self.base_delay
    
    def next_delay(self) -> float:
        """
        Get next delay and increment failure count.
        
        Returns: Delay in seconds
        """
        import random
        
        delay = self._current_delay
        
        # Add jitter
        jitter_range = delay * self.jitter
        delay += random.uniform(-jitter_range, jitter_range)
        
        # Increment for next failure
        self._failure_count += 1
        self._current_delay = min(
            self._current_delay * self.multiplier,
            self.max_delay
        )
        
        logger.debug(
            f"⚠️ Backoff: failure #{self._failure_count}, "
            f"delay={delay:.2f}s, next_delay={self._current_delay:.2f}s"
        )
        
        return delay
    
    def reset(self):
        """Reset backoff after successful operation."""
        if self._failure_count > 0:
            logger.debug(f"✅ Backoff reset after {self._failure_count} failures")
        self._current_delay = self.base_delay
        self._failure_count = 0
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
    
    @property
    def current_delay(self) -> float:
        """Get current delay (without incrementing)."""
        return self._current_delay


class RateLimiter:
    """
    Combined rate limiter with token bucket and exponential backoff.
    
    Provides comprehensive rate limiting for vnstock API:
    - Token bucket for request distribution
    - Exponential backoff for error handling
    - Request tracking and statistics
    """
    
    def __init__(
        self,
        requests_per_minute: int = 6,
        burst_capacity: Optional[int] = None,
        backoff_base: float = 1.0,
        backoff_max: float = 300.0,
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Target rate limit
            burst_capacity: Max burst size (defaults to requests_per_minute)
            backoff_base: Initial backoff delay
            backoff_max: Maximum backoff delay
        """
        # Token bucket for rate limiting
        capacity = burst_capacity or requests_per_minute
        refill_rate = requests_per_minute / 60.0  # tokens per second
        
        self.token_bucket = TokenBucket(
            capacity=float(capacity),
            refill_rate=refill_rate
        )
        
        # Exponential backoff for failures
        self.backoff = ExponentialBackoff(
            base_delay=backoff_base,
            max_delay=backoff_max
        )
        
        # Statistics
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._total_failures = 0
        
        logger.info(
            f"🚀 RateLimiter initialized: "
            f"{requests_per_minute} req/min, "
            f"burst={capacity}, "
            f"backoff={backoff_base}s-{backoff_max}s"
        )
    
    async def acquire(self) -> float:
        """
        Acquire permission for an API request.
        
        Returns: Wait time in seconds
        """
        wait_time = await self.token_bucket.acquire()
        self._total_requests += 1
        self._total_wait_time += wait_time
        return wait_time
    
    async def on_success(self):
        """Call after successful API request."""
        self.backoff.reset()
    
    async def on_failure(self) -> float:
        """
        Call after failed API request.
        
        Returns: Recommended wait time before retry
        """
        self._total_failures += 1
        delay = self.backoff.next_delay()
        
        logger.warning(f"⏳ Backoff delay: {delay:.2f}s after failure")
        await asyncio.sleep(delay)
        
        return delay
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "total_wait_time": round(self._total_wait_time, 2),
            "total_failures": self._total_failures,
            "current_tokens": round(self.token_bucket.available_tokens, 2),
            "failure_count": self.backoff.failure_count,
            "current_backoff_delay": round(self.backoff.current_delay, 2),
        }


# Singleton instance for global rate limiting
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    requests_per_minute: int = 6,
    reset: bool = False
) -> RateLimiter:
    """
    Get or create the global rate limiter instance.
    
    Args:
        requests_per_minute: Rate limit (only used on first call)
        reset: Force create a new instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None or reset:
        _global_rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute
        )
    
    return _global_rate_limiter
