"""Redis client for caching with low latency."""

import json
from typing import Any, Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global Redis connection pool
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get Redis client instance (singleton)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis client initialized", url=settings.REDIS_URL)
    return _redis_client


async def get_redis_client() -> aioredis.Redis:
    """Alias for get_redis() for consistency."""
    return await get_redis()


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


async def get_cache(key: str) -> Optional[Any]:
    """Get value from cache."""
    try:
        redis_client = await get_redis()
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning("Cache get error", key=key, error=str(e))
        return None


async def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache with optional TTL."""
    try:
        redis_client = await get_redis()
        ttl = ttl or settings.REDIS_CACHE_TTL
        serialized = json.dumps(value)
        await redis_client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning("Cache set error", key=key, error=str(e))
        return False


async def delete_cache(key: str) -> bool:
    """Delete key from cache."""
    try:
        redis_client = await get_redis()
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.warning("Cache delete error", key=key, error=str(e))
        return False


