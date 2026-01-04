"""Rate limiting for external API calls."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_requests: int, time_window: int, name: str = "rate_limiter"):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
            name: Name for logging
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.name = name
        self.requests: deque = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit token, waiting if necessary."""
        async with self._lock:
            now = datetime.now()
            cutoff_time = now - timedelta(seconds=self.time_window)
            
            # Remove old requests outside time window
            while self.requests and self.requests[0] < cutoff_time:
                self.requests.popleft()
            
            # Check if we're at the limit
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                sleep_time = (wait_until - now).total_seconds()
                
                if sleep_time > 0:
                    logger.debug(
                        "Rate limit reached, waiting",
                        name=self.name,
                        wait_time=sleep_time,
                        max_requests=self.max_requests
                    )
                    await asyncio.sleep(sleep_time)
                    # Remove expired requests after waiting
                    now = datetime.now()
                    cutoff_time = now - timedelta(seconds=self.time_window)
                    while self.requests and self.requests[0] < cutoff_time:
                        self.requests.popleft()
            
            # Add current request
            self.requests.append(now)
    
    def get_current_count(self) -> int:
        """Get current number of requests in time window."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.time_window)
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
        
        return len(self.requests)

