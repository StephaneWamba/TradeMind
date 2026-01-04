"""Database configuration and async session management."""

import os
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Configure connection pool based on process type
# Workers: smaller pool (sequential task execution)
# API server: larger pool (concurrent WebSocket + HTTP requests)
is_worker = os.environ.get("CELERY_WORKER", "").lower() == "true"

if is_worker:
    pool_size = 5
    max_overflow = 10
    logger.info("Database pool configured for worker process",
                pool_size=pool_size)
else:
    pool_size = 75
    max_overflow = 75
    logger.info("Database pool configured for API server",
                pool_size=pool_size, max_overflow=max_overflow)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=3600,  # Recycle connections after 1 hour
    # Timeout for getting connection from pool (increased for high load)
    pool_timeout=30,
    pool_reset_on_return='commit',  # Reset connections on return to pool
    connect_args={
        "server_settings": {
            "application_name": "trademind",
            "tcp_keepalives_idle": "600",
            "tcp_keepalives_interval": "30",
            "tcp_keepalives_count": "3",
        }
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    FastAPI dependency providing database session.

    Yields:
        AsyncSession: Database session with automatic commit/rollback
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)."""
    from app.models import (  # noqa: F401 - Import models to register them
        exchange,
        strategy,
        trade,
        portfolio,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Log new database connection creation."""
    logger.debug("DB_CONNECTION_CREATED", pool_size=engine.pool.size(),
                 checked_in=engine.pool.checkedin())


@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout and warn on high pool usage."""
    pool = engine.pool
    checked_out = pool.size() - pool.checkedin()
    logger.debug(
        "DB_CONNECTION_CHECKOUT",
        pool_size=pool.size(),
        checked_out=checked_out,
        checked_in=pool.checkedin(),
        overflow=checked_out - pool.size() if checked_out > pool.size() else 0,
    )
    if checked_out >= pool.size() * 0.95:
        logger.warning(
            "DB_POOL_HIGH_USAGE",
            checked_out=checked_out,
            pool_size=pool.size(),
            usage_percent=(checked_out / pool.size()) * 100,
        )


@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """Log connection return to pool."""
    pool = engine.pool
    checked_out = pool.size() - pool.checkedin()
    logger.debug(
        "DB_CONNECTION_CHECKIN",
        pool_size=pool.size(),
        checked_out=checked_out,
        checked_in=pool.checkedin(),
    )
