"""Main API router for v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    automation,
    backtest,
    exchange,
    execution,
    health,
    llm_logs,
    llm_strategy,
    market,
    metrics,
    orders,
    portfolio,
    risk,
    strategy,
    test_email,
    websocket,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    exchange.router, prefix="/exchange", tags=["exchange"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(
    strategy.router, prefix="/strategy", tags=["strategy"])
api_router.include_router(
    llm_strategy.router, prefix="/llm-strategy", tags=["llm-strategy"])
api_router.include_router(
    execution.router, prefix="/execution", tags=["execution"])
api_router.include_router(
    llm_logs.router, prefix="/llm-logs", tags=["llm-logs"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(
    portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(
    metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(
    automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(
    backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(
    test_email.router, prefix="/test-email", tags=["test"])
# WebSocket endpoint (no prefix, direct route)
api_router.include_router(websocket.router, tags=["websocket"])
