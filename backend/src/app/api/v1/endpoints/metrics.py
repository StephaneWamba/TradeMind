"""Business metrics API endpoints for website dashboard."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog

from app.core.database import get_db
from app.models.trade import Trade, Order
from app.models.portfolio import Position
from app.models.strategy import Strategy
from app.domain.risk.portfolio_heat import PortfolioHeatService
from app.domain.risk.management import RiskManagementService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/overview/{connection_id}")
async def get_metrics_overview(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive business metrics overview."""
    try:
        # Get all strategies for this connection
        stmt = select(Strategy).where(Strategy.exchange_connection_id == connection_id)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        strategy_ids = [s.id for s in strategies]

        if not strategy_ids:
            return {
                "connection_id": connection_id,
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0,
                "daily_pnl": 0.0,
                "daily_pnl_percent": 0.0,
                "active_positions": 0,
                "portfolio_heat": 0.0,
                "total_volume": 0.0,
                "avg_trade_size": 0.0,
            }

        # Get closed trades
        stmt = select(Trade).where(
            Trade.strategy_id.in_(strategy_ids),
            Trade.status == "closed"
        )
        result = await db.execute(stmt)
        closed_trades = result.scalars().all()

        # Get open positions
        stmt = select(Position).where(Position.strategy_id.in_(strategy_ids))
        result = await db.execute(stmt)
        positions = result.scalars().all()

        # Calculate metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        total_pnl = sum(t.pnl for t in closed_trades if t.pnl) or 0.0
        total_volume = sum(t.amount * t.entry_price for t in closed_trades) or 0.0
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0.0

        # Daily P&L (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_trades = [t for t in closed_trades if t.exit_time and t.exit_time >= yesterday]
        daily_pnl = sum(t.pnl for t in recent_trades if t.pnl) or 0.0

        # Portfolio heat
        heat_service = PortfolioHeatService(db)
        heat_data = await heat_service.calculate_portfolio_heat(connection_id)

        # Calculate total P&L percent (simplified - would need starting balance)
        total_pnl_percent = 0.0
        daily_pnl_percent = 0.0

        return {
            "connection_id": connection_id,
            "total_trades": total_trades,
            "win_rate": round(win_rate * 100, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_percent": round(daily_pnl_percent, 2),
            "active_positions": len(positions),
            "portfolio_heat": round(heat_data["heat_percent"], 2),
            "total_volume": round(total_volume, 2),
            "avg_trade_size": round(avg_trade_size, 2),
            "winning_trades": len(winning_trades),
            "losing_trades": total_trades - len(winning_trades),
        }

    except Exception as e:
        logger.error("Error fetching metrics overview", connection_id=connection_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{connection_id}")
async def get_performance_metrics(
    connection_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get performance metrics over time."""
    try:
        # Get strategies
        stmt = select(Strategy).where(Strategy.exchange_connection_id == connection_id)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        strategy_ids = [s.id for s in strategies]

        if not strategy_ids:
            return {
                "connection_id": connection_id,
                "period_days": days,
                "daily_returns": [],
                "cumulative_pnl": [],
                "trade_count_by_day": [],
            }

        # Get trades in period
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(Trade).where(
            Trade.strategy_id.in_(strategy_ids),
            Trade.status == "closed",
            Trade.exit_time >= start_date
        )
        result = await db.execute(stmt)
        trades = result.scalars().all()

        # Group by day
        daily_data = {}
        for trade in trades:
            if trade.exit_time:
                day = trade.exit_time.date()
                if day not in daily_data:
                    daily_data[day] = {"pnl": 0.0, "count": 0}
                daily_data[day]["pnl"] += trade.pnl or 0.0
                daily_data[day]["count"] += 1

        # Build time series
        daily_returns = []
        cumulative_pnl = []
        trade_count_by_day = []
        running_total = 0.0

        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=days - i - 1)).date()
            day_pnl = daily_data.get(date, {}).get("pnl", 0.0)
            day_count = daily_data.get(date, {}).get("count", 0)
            running_total += day_pnl

            daily_returns.append({
                "date": date.isoformat(),
                "pnl": round(day_pnl, 2),
            })
            cumulative_pnl.append({
                "date": date.isoformat(),
                "cumulative": round(running_total, 2),
            })
            trade_count_by_day.append({
                "date": date.isoformat(),
                "count": day_count,
            })

        return {
            "connection_id": connection_id,
            "period_days": days,
            "daily_returns": daily_returns,
            "cumulative_pnl": cumulative_pnl,
            "trade_count_by_day": trade_count_by_day,
        }

    except Exception as e:
        logger.error("Error fetching performance metrics", connection_id=connection_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/{connection_id}")
async def get_risk_metrics(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get risk metrics."""
    try:
        # Get strategies
        stmt = select(Strategy).where(Strategy.exchange_connection_id == connection_id)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        strategy_ids = [s.id for s in strategies]

        # Portfolio heat
        heat_service = PortfolioHeatService(db)
        heat_data = await heat_service.calculate_portfolio_heat(connection_id)

        # Risk metrics per strategy
        risk_service = RiskManagementService(db)
        strategy_risks = []
        
        for strategy in strategies:
            risk_config = await risk_service.get_risk_config(strategy.id)
            portfolio_metrics = await risk_service.calculate_portfolio_risk_metrics(strategy.id)
            daily_loss_check = await risk_service.check_daily_loss_limit(strategy.id)
            circuit_breaker = await risk_service.check_circuit_breaker(strategy.id)

            strategy_risks.append({
                "strategy_id": strategy.id,
                "strategy_name": strategy.name,
                "max_position_size_percent": risk_config.max_position_size_percent * 100,
                "max_daily_loss_percent": risk_config.max_daily_loss_percent * 100,
                "current_daily_loss": daily_loss_check["current_loss"],
                "daily_loss_limit_reached": daily_loss_check["limit_reached"],
                "circuit_breaker_active": circuit_breaker,
                "win_rate": portfolio_metrics.get("win_rate", 0.0) * 100,
                "max_drawdown": portfolio_metrics.get("max_drawdown", 0.0),
                "sharpe_ratio": portfolio_metrics.get("sharpe_ratio", 0.0),
            })

        return {
            "connection_id": connection_id,
            "portfolio_heat": {
                "current_heat": round(heat_data["heat_percent"], 2),
                "total_risk_usdt": round(heat_data["total_risk_usdt"], 2),
                "position_count": heat_data["position_count"],
            },
            "strategy_risks": strategy_risks,
        }

    except Exception as e:
        logger.error("Error fetching risk metrics", connection_id=connection_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/stats/{connection_id}")
async def get_trade_statistics(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get trade statistics."""
    try:
        # Get strategies
        stmt = select(Strategy).where(Strategy.exchange_connection_id == connection_id)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        strategy_ids = [s.id for s in strategies]

        if not strategy_ids:
            return {
                "connection_id": connection_id,
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "profit_factor": 0.0,
            }

        # Get closed trades
        stmt = select(Trade).where(
            Trade.strategy_id.in_(strategy_ids),
            Trade.status == "closed"
        )
        result = await db.execute(stmt)
        trades = result.scalars().all()

        if not trades:
            return {
                "connection_id": connection_id,
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t.pnl for t in trades if t.pnl and t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl and t.pnl < 0]

        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        return {
            "connection_id": connection_id,
            "total_trades": len(trades),
            "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
            "avg_loss": round(abs(sum(losses) / len(losses)), 2) if losses else 0.0,
            "largest_win": round(max(wins), 2) if wins else 0.0,
            "largest_loss": round(min(losses), 2) if losses else 0.0,
            "profit_factor": round(profit_factor, 2),
            "total_wins": round(total_wins, 2),
            "total_losses": round(total_losses, 2),
        }

    except Exception as e:
        logger.error("Error fetching trade statistics", connection_id=connection_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

