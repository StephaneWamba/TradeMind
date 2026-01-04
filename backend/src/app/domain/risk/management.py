"""Risk management domain logic for position sizing, loss limits, and circuit breakers."""

import math
from datetime import datetime, timezone, date
from typing import Optional

import structlog
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.risk import CircuitBreaker, DailyLoss, RiskConfig
from app.models.trade import Trade
from app.models.strategy import Strategy
from app.services.notification.alerting import AlertingService

logger = structlog.get_logger(__name__)


class RiskManagementService:
    """Service for risk management including position sizing, loss limits, and circuit breakers."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.alerting_service = AlertingService()

    async def calculate_position_size(
        self,
        strategy_id: int,
        account_balance: float,
        method: str = "fixed",
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        atr: Optional[float] = None,
        current_price: Optional[float] = None,
        stop_loss_percent: Optional[float] = None,
    ) -> float:
        """
        Calculate position size using specified method.

        Args:
            strategy_id: Strategy ID
            account_balance: Current account balance in USDT
            method: Position sizing method ('fixed', 'kelly', or 'atr')
            win_rate: Win rate for Kelly criterion (0.0-1.0)
            avg_win: Average win amount for Kelly criterion
            avg_loss: Average loss amount for Kelly criterion
            atr: Average True Range for volatility-based sizing
            current_price: Current market price (for ATR-based sizing)
            stop_loss_percent: Stop-loss percentage (for ATR-based sizing)

        Returns:
            Position size in USDT
        """
        risk_config = await self.get_risk_config(strategy_id)
        max_position_size = account_balance * risk_config.max_position_size_percent

        if method == "fixed":
            position_size = account_balance * settings.DEFAULT_POSITION_SIZE_PERCENT
            return min(position_size, max_position_size)

        elif method == "kelly":
            if win_rate is None or avg_win is None or avg_loss is None:
                logger.warning(
                    "Kelly criterion requires win_rate, avg_win, avg_loss - using fixed")
                return account_balance * settings.DEFAULT_POSITION_SIZE_PERCENT

            if avg_loss == 0:
                logger.warning("Average loss is zero - using fixed")
                return account_balance * settings.DEFAULT_POSITION_SIZE_PERCENT

            win_loss_ratio = avg_win / avg_loss
            loss_rate = 1 - win_rate

            kelly_fraction = (win_rate * win_loss_ratio -
                              loss_rate) / win_loss_ratio
            kelly_fraction = kelly_fraction * 0.25
            kelly_fraction = max(0.0, min(kelly_fraction, 0.02))

            position_size = account_balance * kelly_fraction
            return min(position_size, max_position_size)

        elif method == "atr":
            if atr is None or current_price is None or stop_loss_percent is None:
                logger.warning(
                    "ATR-based sizing requires atr, current_price, stop_loss_percent - using fixed")
                return account_balance * settings.DEFAULT_POSITION_SIZE_PERCENT

            risk_amount = account_balance * 0.01
            stop_loss_distance = current_price * stop_loss_percent
            effective_stop_distance = max(stop_loss_distance, atr * 0.5)
            position_size_usdt = risk_amount / \
                (effective_stop_distance / current_price)

            return min(position_size_usdt, max_position_size)

        else:
            return account_balance * settings.DEFAULT_POSITION_SIZE_PERCENT

    async def check_daily_loss_limit(self, strategy_id: int) -> dict[str, any]:
        """
        Check if daily loss limit has been reached.

        Returns:
            Dict with 'limit_reached' bool and 'current_loss' float
        """
        risk_config = await self.get_risk_config(strategy_id)
        today = date.today()

        stmt = select(DailyLoss).where(
            DailyLoss.strategy_id == strategy_id,
            sql_func.date(DailyLoss.date) == today,
        )
        result = await self.db.execute(stmt)
        daily_loss = result.scalar_one_or_none()

        if not daily_loss:
            return {"limit_reached": False, "current_loss": 0.0, "limit": risk_config.max_daily_loss_percent}

        limit_reached = daily_loss.total_loss_percent >= risk_config.max_daily_loss_percent

        if limit_reached and not daily_loss.limit_reached:
            await self.alerting_service.alert_daily_loss_limit(
                strategy_id=strategy_id,
                current_loss=daily_loss.total_loss_percent,
                limit=risk_config.max_daily_loss_percent,
            )
            await self.trigger_circuit_breaker(
                strategy_id, f"Daily loss limit reached: {daily_loss.total_loss_percent:.2f}%"
            )
            daily_loss.limit_reached = True
            await self.db.commit()

        return {
            "limit_reached": limit_reached,
            "current_loss": daily_loss.total_loss_percent,
            "limit": risk_config.max_daily_loss_percent,
        }

    async def update_daily_loss(self, strategy_id: int, trade_pnl: float, account_balance: float):
        """Update daily loss tracking after a trade."""
        today = date.today()

        stmt = select(DailyLoss).where(
            DailyLoss.strategy_id == strategy_id,
            sql_func.date(DailyLoss.date) == today,
        )
        result = await self.db.execute(stmt)
        daily_loss = result.scalar_one_or_none()

        if not daily_loss:
            daily_loss = DailyLoss(
                strategy_id=strategy_id,
                date=datetime.now(timezone.utc),
                total_loss=0.0,
                total_loss_percent=0.0,
                trade_count=0,
            )
            self.db.add(daily_loss)

        if trade_pnl < 0:
            daily_loss.total_loss += abs(trade_pnl)
            daily_loss.total_loss_percent = (
                daily_loss.total_loss / account_balance) * 100

        daily_loss.trade_count += 1
        await self.db.commit()

        await self.check_daily_loss_limit(strategy_id)

    async def check_circuit_breaker(self, strategy_id: int) -> bool:
        """Check if circuit breaker is triggered for a strategy."""
        stmt = select(CircuitBreaker).where(
            CircuitBreaker.strategy_id == strategy_id)
        result = await self.db.execute(stmt)
        circuit_breaker = result.scalar_one_or_none()

        if not circuit_breaker:
            return False

        return circuit_breaker.is_triggered

    async def trigger_circuit_breaker(self, strategy_id: int, reason: str):
        """Trigger circuit breaker for a strategy."""
        stmt = select(CircuitBreaker).where(
            CircuitBreaker.strategy_id == strategy_id)
        result = await self.db.execute(stmt)
        circuit_breaker = result.scalar_one_or_none()

        if not circuit_breaker:
            circuit_breaker = CircuitBreaker(
                strategy_id=strategy_id,
                is_triggered=False,
            )
            self.db.add(circuit_breaker)

        circuit_breaker.is_triggered = True
        circuit_breaker.trigger_reason = reason
        circuit_breaker.triggered_at = datetime.now(timezone.utc)

        stmt = select(Strategy).where(Strategy.id == strategy_id)
        result = await self.db.execute(stmt)
        strategy = result.scalar_one_or_none()
        if strategy:
            strategy.status = "paused"
            strategy.is_active = False

        await self.db.commit()

        await self.alerting_service.alert_circuit_breaker(
            strategy_id=strategy_id,
            reason=reason,
        )

        logger.warning(
            "Circuit breaker triggered",
            strategy_id=strategy_id,
            reason=reason,
        )

    async def reset_circuit_breaker(self, strategy_id: int):
        """Reset circuit breaker for a strategy."""
        stmt = select(CircuitBreaker).where(
            CircuitBreaker.strategy_id == strategy_id)
        result = await self.db.execute(stmt)
        circuit_breaker = result.scalar_one_or_none()

        if circuit_breaker:
            circuit_breaker.is_triggered = False
            circuit_breaker.trigger_reason = None
            circuit_breaker.triggered_at = None
            await self.db.commit()

        logger.info("Circuit breaker reset", strategy_id=strategy_id)

    async def get_risk_config(self, strategy_id: int) -> RiskConfig:
        """Get or create risk configuration for a strategy."""
        stmt = select(RiskConfig).where(RiskConfig.strategy_id == strategy_id)
        result = await self.db.execute(stmt)
        risk_config = result.scalar_one_or_none()

        if not risk_config:
            risk_config = RiskConfig(
                strategy_id=strategy_id,
                max_position_size_percent=settings.MAX_POSITION_SIZE_PERCENT,
                max_daily_loss_percent=settings.MAX_DAILY_LOSS_PERCENT,
                max_drawdown_percent=settings.MAX_DRAWDOWN_PERCENT,
                min_confidence_threshold=0.5,
                position_sizing_method="fixed",
            )
            self.db.add(risk_config)
            await self.db.commit()
            await self.db.refresh(risk_config)

        return risk_config

    async def update_risk_config(
        self,
        strategy_id: int,
        max_position_size_percent: Optional[float] = None,
        max_daily_loss_percent: Optional[float] = None,
        max_drawdown_percent: Optional[float] = None,
        min_confidence_threshold: Optional[float] = None,
        position_sizing_method: Optional[str] = None,
    ) -> RiskConfig:
        """Update risk configuration for a strategy."""
        risk_config = await self.get_risk_config(strategy_id)

        if max_position_size_percent is not None:
            risk_config.max_position_size_percent = max_position_size_percent
        if max_daily_loss_percent is not None:
            risk_config.max_daily_loss_percent = max_daily_loss_percent
        if max_drawdown_percent is not None:
            risk_config.max_drawdown_percent = max_drawdown_percent
        if min_confidence_threshold is not None:
            risk_config.min_confidence_threshold = min_confidence_threshold
        if position_sizing_method is not None:
            risk_config.position_sizing_method = position_sizing_method

        await self.db.commit()
        await self.db.refresh(risk_config)

        logger.info("Risk config updated", strategy_id=strategy_id)
        return risk_config

    async def calculate_portfolio_risk_metrics(self, strategy_id: int) -> dict[str, float]:
        """Calculate portfolio risk metrics for a strategy."""
        stmt = select(Trade).where(
            Trade.strategy_id == strategy_id,
            Trade.status == "closed",
        )
        result = await self.db.execute(stmt)
        trades = result.scalars().all()

        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

        wins = [t.pnl for t in trades if t.pnl and t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl and t.pnl < 0]

        win_rate = len(wins) / len(trades) if trades else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in sorted(trades, key=lambda t: t.exit_time or t.created_at):
            if trade.pnl:
                cumulative_pnl += trade.pnl
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = peak - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        returns = [t.pnl_percent /
                   100 if t.pnl_percent else 0.0 for t in trades]
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(
                sum((r - avg_return) ** 2 for r in returns) / len(returns))
            sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        return {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
        }

    async def emergency_stop(self, strategy_id: Optional[int] = None):
        """
        Emergency stop - pause all strategies or a specific strategy.

        Args:
            strategy_id: If provided, stop only this strategy. If None, stop all.
        """
        if strategy_id:
            await self.trigger_circuit_breaker(strategy_id, "Emergency stop triggered")
        else:
            stmt = select(Strategy).where(Strategy.is_active == True)
            result = await self.db.execute(stmt)
            strategies = result.scalars().all()

            for strategy in strategies:
                await self.trigger_circuit_breaker(strategy.id, "Emergency stop - all strategies")

        logger.critical("Emergency stop executed", strategy_id=strategy_id)
