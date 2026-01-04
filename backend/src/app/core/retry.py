"""Retry logic with exponential backoff for transient failures."""

import asyncio
from typing import TypeVar, Callable, Awaitable, Tuple, Any
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,),
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Retry function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e

            if attempt < max_retries:
                logger.warning(
                    "Retry attempt failed, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e)
                )
                await asyncio.sleep(min(delay, max_delay))
                delay *= backoff_factor
            else:
                logger.error(
                    "All retry attempts exhausted",
                    max_retries=max_retries,
                    error=str(e)
                )
                raise last_exception

    # Should never reach here, but for type safety
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error")
