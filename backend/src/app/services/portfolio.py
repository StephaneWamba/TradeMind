"""Portfolio management service for tracking performance and P&L."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio, Position
from app.models.trade import Trade
from app.models.exchange import ExchangeConnection
from app.services.exchange import ExchangeService
from app.domain.trading.position import PositionService
from app.core.redis import get_cache, set_cache

logger = structlog.get_logger(__name__)


class PortfolioService:
    """Service for portfolio tracking, P&L calculation, and performance analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)
        self.position_service = PositionService(db)

    async def calculate_portfolio_value(
        self, connection_id: int, strategy_id: Optional[int] = None, use_cache: bool = True
    ) -> dict:
        """
        Calculate current portfolio value including cash and positions.

        OPTIMIZED: Uses cached balance data and skips blocking position updates.

        Args:
            connection_id: Exchange connection ID
            strategy_id: Optional strategy filter
            use_cache: If True, uses cached balance (faster but may be slightly stale)

        Returns:
            {
                "total_value_usdt": float,
                "cash_usdt": float,
                "invested_usdt": float,
                "unrealized_pnl": float,
                "unrealized_pnl_percent": float,
                "positions": [...]
            }
        """
        # OPTIMIZATION: Get cash balance from cache first (fast path)
        cash_usdt = 0.0
        if use_cache:
            cache_key = f"balance:{connection_id}"
            cached_balance = await get_cache(cache_key)
            if cached_balance:
                cash_usdt = cached_balance.get("usdt", 0.0)
                logger.debug("Using cached balance",
                             connection_id=connection_id)

        # If no cache or cache miss, fetch balance (but don't block if it fails)
        if not cash_usdt:
            try:
                balance = await self.exchange_service.get_balance(connection_id)
                cash_usdt = balance.get("usdt", 0.0) if balance else 0.0
            except Exception as e:
                logger.warning("Failed to get balance, using 0",
                               connection_id=connection_id, error=str(e))
                cash_usdt = 0.0

        # Get open positions with error handling (fast DB query)
        # Filter by connection_id to get only positions for this connection
        try:
            positions = await self.position_service.get_positions(
                strategy_id=strategy_id,
                connection_id=connection_id
            )
        except Exception as e:
            logger.warning(
                "Failed to get positions, using empty list", error=str(e))
            positions = []

        # OPTIMIZATION: Skip blocking position price updates
        # Position prices are updated by background WebSocket tasks
        # This endpoint just reads current values from DB (fast)

        # Calculate invested value and unrealized P&L from existing position data
        invested_usdt = 0.0
        unrealized_pnl = 0.0
        position_values = []

        for position in positions:
            # Use current_price if available, fallback to entry_price
            current_price = position.current_price or position.entry_price
            position_value = position.amount * current_price
            invested_usdt += position_value
            unrealized_pnl += position.unrealized_pnl or 0.0

            position_values.append({
                "id": position.id,
                "symbol": position.symbol,
                "amount": position.amount,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "value_usdt": position_value,
                "unrealized_pnl": position.unrealized_pnl or 0.0,
                "unrealized_pnl_percent": position.unrealized_pnl_percent or 0.0,
            })

        total_value_usdt = cash_usdt + invested_usdt
        unrealized_pnl_percent = (
            (unrealized_pnl / invested_usdt * 100) if invested_usdt > 0 else 0.0
        )

        return {
            "total_value_usdt": total_value_usdt,
            "cash_usdt": cash_usdt,
            "invested_usdt": invested_usdt,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": unrealized_pnl_percent,
            "positions": position_values,
            "position_count": len(positions),
        }

    async def calculate_realized_pnl(
        self, strategy_id: Optional[int] = None, days: Optional[int] = None
    ) -> dict:
        """
        Calculate realized P&L from closed trades.

        Args:
            strategy_id: Optional strategy filter
            days: Optional number of days to look back (None = all time)
        """
        stmt = select(Trade).where(Trade.status == "closed")

        if strategy_id:
            stmt = stmt.where(Trade.strategy_id == strategy_id)

        if days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(Trade.exit_time >= cutoff_date)

        result = await self.db.execute(stmt)
        trades = result.scalars().all()

        total_pnl = sum(trade.pnl or 0.0 for trade in trades)
        total_pnl_percent = sum(trade.pnl_percent or 0.0 for trade in trades)
        win_count = sum(1 for trade in trades if (trade.pnl or 0.0) > 0)
        loss_count = sum(1 for trade in trades if (trade.pnl or 0.0) < 0)

        return {
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "total_trades": len(trades),
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": (win_count / len(trades) * 100) if trades else 0.0,
        }

    async def create_portfolio_snapshot(
        self, connection_id: int, strategy_id: Optional[int] = None
    ) -> Portfolio:
        """
        Create a portfolio snapshot with current values.

        Returns:
            Portfolio model instance
        """
        portfolio_value = await self.calculate_portfolio_value(connection_id, strategy_id)
        realized_pnl = await self.calculate_realized_pnl(strategy_id, days=1)

        # Get yesterday's snapshot for daily P&L calculation
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        stmt = select(Portfolio).where(
            Portfolio.created_at >= yesterday
        ).order_by(Portfolio.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        yesterday_snapshot = result.scalar_one_or_none()

        total_pnl = realized_pnl["total_pnl"] + \
            portfolio_value["unrealized_pnl"]
        total_pnl_percent = (
            (total_pnl / portfolio_value["total_value_usdt"] * 100)
            if portfolio_value["total_value_usdt"] > 0
            else 0.0
        )

        if yesterday_snapshot:
            daily_pnl = portfolio_value["total_value_usdt"] - \
                yesterday_snapshot.total_value_usdt
            daily_pnl_percent = (
                (daily_pnl / yesterday_snapshot.total_value_usdt * 100)
                if yesterday_snapshot.total_value_usdt > 0
                else 0.0
            )
        else:
            daily_pnl = 0.0
            daily_pnl_percent = 0.0

        snapshot = Portfolio(
            total_value_usdt=portfolio_value["total_value_usdt"],
            cash_usdt=portfolio_value["cash_usdt"],
            invested_usdt=portfolio_value["invested_usdt"],
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            daily_pnl=daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
        )

        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(
            "Portfolio snapshot created",
            snapshot_id=snapshot.id,
            total_value=portfolio_value["total_value_usdt"],
            total_pnl=total_pnl,
        )

        return snapshot

    async def get_portfolio_overview(
        self, connection_id: int, strategy_id: Optional[int] = None
    ) -> dict:
        """
        Get comprehensive portfolio overview.

        OPTIMIZED: Returns cached data immediately, updates cache in background.

        Returns:
            {
                "current_value": {...},
                "realized_pnl": {...},
                "performance_metrics": {...},
                "asset_allocation": {...}
            }
        """
        # OPTIMIZATION: Check cache first for instant response
        cache_key = f"portfolio_overview:{connection_id}:{strategy_id or 'all'}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug("Portfolio overview cache hit",
                         connection_id=connection_id)
            # Update cache in background (fire and forget)
            asyncio.create_task(self._update_portfolio_cache(
                connection_id, strategy_id, cache_key))
            return cached

        # Cache miss - calculate and return (will be slower but still optimized)
        return await self._calculate_and_cache_overview(connection_id, strategy_id, cache_key)

    async def _calculate_and_cache_overview(
        self, connection_id: int, strategy_id: Optional[int], cache_key: str
    ) -> dict:
        """Calculate portfolio overview and cache it."""
        # Current portfolio value - OPTIMIZED: uses cached balance, skips blocking updates
        try:
            current_value = await self.calculate_portfolio_value(connection_id, strategy_id, use_cache=True)
        except Exception as e:
            logger.error("Failed to calculate portfolio value", error=str(e))
            current_value = {
                "total_value_usdt": 0.0,
                "cash_usdt": 0.0,
                "invested_usdt": 0.0,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_percent": 0.0,
                "positions": [],
                "position_count": 0,
            }

        # Realized P&L (all time and today) - with error handling
        try:
            realized_pnl_all = await self.calculate_realized_pnl(strategy_id)
        except Exception as e:
            logger.warning(
                "Failed to calculate realized P&L (all)", error=str(e))
            realized_pnl_all = {"total_pnl": 0.0,
                                "total_pnl_percent": 0.0, "trade_count": 0}

        try:
            realized_pnl_today = await self.calculate_realized_pnl(strategy_id, days=1)
        except Exception as e:
            logger.warning(
                "Failed to calculate realized P&L (today)", error=str(e))
            realized_pnl_today = {"total_pnl": 0.0,
                                  "total_pnl_percent": 0.0, "trade_count": 0}

        # Performance metrics - with error handling
        try:
            performance = await self.calculate_performance_metrics(strategy_id)
        except Exception as e:
            logger.warning(
                "Failed to calculate performance metrics", error=str(e))
            performance = {}

        # Asset allocation - with error handling
        try:
            allocation = await self.calculate_asset_allocation(connection_id, strategy_id)
        except Exception as e:
            logger.warning(
                "Failed to calculate asset allocation", error=str(e))
            allocation = {"cash_percent": 100.0, "allocations": []}

        # Calculate daily P&L from current value
        daily_pnl = current_value.get(
            "unrealized_pnl", 0.0) + realized_pnl_today.get("total_pnl", 0.0)
        daily_pnl_percent = (
            (daily_pnl / current_value["total_value_usdt"] * 100)
            if current_value["total_value_usdt"] > 0
            else 0.0
        )

        overview = {
            "total_value_usdt": current_value["total_value_usdt"],
            "cash_usdt": current_value["cash_usdt"],
            "invested_usdt": current_value["invested_usdt"],
            "unrealized_pnl": current_value["unrealized_pnl"],
            "unrealized_pnl_percent": current_value["unrealized_pnl_percent"],
            "daily_pnl": daily_pnl,
            "daily_pnl_percent": daily_pnl_percent,
            "current_value": current_value,
            "realized_pnl": {
                "all_time": realized_pnl_all,
                "today": realized_pnl_today,
            },
            "performance_metrics": performance,
            "asset_allocation": allocation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Cache the result for 10 seconds (fast updates but not too frequent)
        await set_cache(cache_key, overview, ttl=10)
        logger.debug("Portfolio overview cached", connection_id=connection_id)

        return overview

    async def _update_portfolio_cache(
        self, connection_id: int, strategy_id: Optional[int], cache_key: str
    ):
        """Update portfolio cache in background (non-blocking)."""
        try:
            # Recalculate with fresh data (may be slower)
            overview = await self._calculate_and_cache_overview(connection_id, strategy_id, cache_key)
            logger.debug("Portfolio cache updated in background",
                         connection_id=connection_id)
        except Exception as e:
            logger.warning("Failed to update portfolio cache in background",
                           connection_id=connection_id, error=str(e))

    async def calculate_performance_metrics(
        self, strategy_id: Optional[int] = None
    ) -> dict:
        """
        Calculate performance metrics: Sharpe ratio, max drawdown, etc.

        Returns:
            {
                "total_return": float,
                "total_return_percent": float,
                "sharpe_ratio": float,
                "max_drawdown": float,
                "max_drawdown_percent": float,
                "best_day": float,
                "worst_day": float,
                "avg_daily_return": float,
            }
        """
        # Get all portfolio snapshots
        stmt = select(Portfolio).order_by(Portfolio.created_at.asc())
        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        if not snapshots:
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

        # Calculate returns
        initial_value = snapshots[0].total_value_usdt
        current_value = snapshots[-1].total_value_usdt
        total_return = current_value - initial_value
        total_return_percent = (
            (total_return / initial_value * 100) if initial_value > 0 else 0.0
        )

        # Calculate daily returns
        daily_returns = []
        peak_value = initial_value
        max_drawdown = 0.0
        max_drawdown_percent = 0.0

        for i in range(1, len(snapshots)):
            prev_value = snapshots[i - 1].total_value_usdt
            curr_value = snapshots[i].total_value_usdt
            daily_return = curr_value - prev_value
            daily_return_percent = (
                (daily_return / prev_value * 100) if prev_value > 0 else 0.0
            )
            daily_returns.append(daily_return_percent)

            # Track peak and drawdown
            if curr_value > peak_value:
                peak_value = curr_value

            drawdown = peak_value - curr_value
            drawdown_percent = (drawdown / peak_value *
                                100) if peak_value > 0 else 0.0

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent

        # Calculate Sharpe ratio (simplified: mean return / std deviation)
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - avg_return) **
                           2 for r in daily_returns) / len(daily_returns)
            std_dev = variance ** 0.5
            sharpe_ratio = (avg_return / std_dev) if std_dev > 0 else 0.0
        else:
            avg_return = 0.0
            sharpe_ratio = 0.0

        best_day = max(daily_returns) if daily_returns else 0.0
        worst_day = min(daily_returns) if daily_returns else 0.0

        return {
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "max_drawdown_percent": max_drawdown_percent,
            "best_day": best_day,
            "worst_day": worst_day,
            "avg_daily_return": avg_return,
        }

    async def calculate_asset_allocation(
        self, connection_id: int, strategy_id: Optional[int] = None
    ) -> dict:
        """
        Calculate asset allocation across different cryptocurrencies.

        Returns:
            {
                "cash_percent": float,
                "allocations": [
                    {"symbol": str, "value_usdt": float, "percent": float}
                ]
            }
        """
        portfolio_value = await self.calculate_portfolio_value(connection_id, strategy_id)
        total_value = portfolio_value["total_value_usdt"]

        if total_value == 0:
            return {
                "cash_percent": 0.0,
                "allocations": [],
            }

        cash_percent = (portfolio_value["cash_usdt"] / total_value * 100)

        # Group positions by symbol
        allocations = {}
        for pos in portfolio_value["positions"]:
            symbol = pos["symbol"]
            if symbol not in allocations:
                allocations[symbol] = 0.0
            allocations[symbol] += pos["value_usdt"]

        # Convert to list with percentages
        allocation_list = [
            {
                "symbol": symbol,
                "value_usdt": value,
                "percent": (value / total_value * 100),
            }
            for symbol, value in allocations.items()
        ]

        return {
            "cash_percent": cash_percent,
            "allocations": allocation_list,
        }

    async def get_portfolio_history(
        self, days: int = 30, strategy_id: Optional[int] = None
    ) -> list[dict]:
        """
        Get portfolio value history for charting.

        Args:
            days: Number of days of history
            strategy_id: Optional strategy filter

        Returns:
            List of portfolio snapshots
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(Portfolio).where(
            Portfolio.created_at >= cutoff_date
        ).order_by(Portfolio.created_at.asc())

        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        return [
            {
                "date": snapshot.created_at.isoformat(),
                "total_value_usdt": snapshot.total_value_usdt,
                "cash_usdt": snapshot.cash_usdt,
                "invested_usdt": snapshot.invested_usdt,
                "total_pnl": snapshot.total_pnl,
                "total_pnl_percent": snapshot.total_pnl_percent,
                "daily_pnl": snapshot.daily_pnl,
                "daily_pnl_percent": snapshot.daily_pnl_percent,
            }
            for snapshot in snapshots
        ]
