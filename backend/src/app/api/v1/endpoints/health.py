"""Health check endpoints."""

import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/detailed")
async def health_detailed(db: AsyncSession = Depends(get_db)):
    """Detailed health check with component status."""
    components = {
        "api": {"status": "healthy", "latency_ms": 0},
        "database": {"status": "unknown", "latency_ms": None},
        "redis": {"status": "unknown", "latency_ms": None},
    }

    overall_status = "healthy"

    # Check database
    try:
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        latency_ms = (time.time() - start_time) * 1000
        components["database"] = {"status": "healthy",
                                  "latency_ms": round(latency_ms, 2)}
        logger.debug("Database health check passed", latency_ms=latency_ms)
    except Exception as e:
        components["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
        logger.error("Database health check failed", error=str(e))

    # Check Redis
    try:
        start_time = time.time()
        redis_client = await get_redis()
        await redis_client.ping()
        latency_ms = (time.time() - start_time) * 1000
        components["redis"] = {"status": "healthy",
                               "latency_ms": round(latency_ms, 2)}
        logger.debug("Redis health check passed", latency_ms=latency_ms)
    except Exception as e:
        components["redis"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
        logger.error("Redis health check failed", error=str(e))

    return {
        "status": overall_status,
        "components": components,
    }
