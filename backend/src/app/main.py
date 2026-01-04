"""FastAPI application entry point."""

import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.core.websocket_event_consumer import websocket_event_consumer

configure_logging(settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware for request timing and performance monitoring."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )
            if process_time > 1.0:
                logger.warning(
                    "slow_request",
                    method=request.method,
                    path=request.url.path,
                    process_time_ms=round(process_time * 1000, 2),
                )
            if process_time > 5.0:
                logger.error(
                    "very_slow_request",
                    method=request.method,
                    path=request.url.path,
                    process_time_ms=round(process_time * 1000, 2),
                )
            return response
        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time_ms=round(process_time * 1000, 2),
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    logger.info("Starting TradeMind backend")
    await init_db()
    logger.info("Database initialized")

    await websocket_event_consumer.start()
    logger.info("WebSocket event consumer started")

    yield

    logger.info("Shutting down TradeMind backend")
    await websocket_event_consumer.stop()
    logger.info("WebSocket event consumer stopped")


app = FastAPI(
    title="TradeMind API",
    description="Autonomous trading bot platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestTimingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "trademind-backend"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "TradeMind API", "version": "0.1.0"}
