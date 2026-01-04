"""Portfolio management API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.portfolio import PortfolioService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/overview")
async def get_portfolio_overview(
    connection_id: int = Query(..., description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive portfolio overview."""
    try:
        service = PortfolioService(db)
        overview = await service.get_portfolio_overview(connection_id, strategy_id)
        return overview
    except Exception as e:
        logger.error("Failed to get portfolio overview", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/value")
async def get_portfolio_value(
    connection_id: int = Query(..., description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Get current portfolio value."""
    try:
        service = PortfolioService(db)
        value = await service.calculate_portfolio_value(connection_id, strategy_id)
        return value
    except Exception as e:
        logger.error("Failed to calculate portfolio value", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl")
async def get_realized_pnl(
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    days: Optional[int] = Query(
        None, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
):
    """Get realized P&L from closed trades."""
    try:
        service = PortfolioService(db)
        pnl = await service.calculate_realized_pnl(strategy_id, days)
        return pnl
    except Exception as e:
        logger.error("Failed to calculate realized P&L", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(
    connection_id: Optional[int] = Query(
        None, description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Get performance metrics (Sharpe ratio, max drawdown, etc.)."""
    try:
        # If connection_id provided but no strategy_id, get all strategies for that connection
        if connection_id and not strategy_id:
            from app.models.strategy import Strategy
            stmt = select(Strategy).where(
                Strategy.exchange_connection_id == connection_id)
            result = await db.execute(stmt)
            strategies = result.scalars().all()
            if strategies:
                # Calculate metrics for all strategies combined (pass None to get all)
                strategy_id = None
            else:
                # No strategies found for this connection, return empty metrics
                return {
                    "total_return": 0.0,
                    "total_return_percent": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "max_drawdown_percent": 0.0,
                    "best_day": 0.0,
                    "worst_day": 0.0,
                    "avg_daily_return": 0.0,
                }

        service = PortfolioService(db)
        metrics = await service.calculate_performance_metrics(strategy_id)
        return metrics
    except Exception as e:
        logger.error("Failed to calculate performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation")
async def get_asset_allocation(
    connection_id: int = Query(..., description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Get asset allocation breakdown."""
    try:
        service = PortfolioService(db)
        allocation = await service.calculate_asset_allocation(connection_id, strategy_id)
        return allocation
    except Exception as e:
        logger.error("Failed to calculate asset allocation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_portfolio_history(
    connection_id: Optional[int] = Query(
        None, description="Exchange connection ID"),
    days: int = Query(30, description="Number of days of history"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio value history for charting."""
    try:
        # If connection_id provided but no strategy_id, get all strategies for that connection
        if connection_id and not strategy_id:
            from app.models.strategy import Strategy
            stmt = select(Strategy).where(
                Strategy.exchange_connection_id == connection_id)
            result = await db.execute(stmt)
            strategies = result.scalars().all()
            if not strategies:
                # No strategies found, return empty history
                return {"history": [], "days": days}
            # Use None to get history for all strategies (or could filter by connection_id in service)
            strategy_id = None

        service = PortfolioService(db)
        history = await service.get_portfolio_history(days, strategy_id)
        return {"history": history, "days": days}
    except Exception as e:
        logger.error("Failed to get portfolio history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot")
async def create_portfolio_snapshot(
    connection_id: int = Query(..., description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(
        None, description="Optional strategy filter"),
    db: AsyncSession = Depends(get_db),
):
    """Create a portfolio snapshot."""
    try:
        service = PortfolioService(db)
        snapshot = await service.create_portfolio_snapshot(connection_id, strategy_id)
        return {
            "id": snapshot.id,
            "total_value_usdt": snapshot.total_value_usdt,
            "cash_usdt": snapshot.cash_usdt,
            "invested_usdt": snapshot.invested_usdt,
            "total_pnl": snapshot.total_pnl,
            "total_pnl_percent": snapshot.total_pnl_percent,
            "daily_pnl": snapshot.daily_pnl,
            "daily_pnl_percent": snapshot.daily_pnl_percent,
            "created_at": snapshot.created_at.isoformat(),
        }
    except Exception as e:
        logger.error("Failed to create portfolio snapshot", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
