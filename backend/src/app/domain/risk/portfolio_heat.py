"""Portfolio heat tracking domain logic for total risk exposure."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Position
from app.models.strategy import Strategy
from app.services.notification.alerting import AlertingService

logger = structlog.get_logger(__name__)


class PortfolioHeatService:
    """Service for tracking portfolio heat (total risk exposure)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.alerting_service = AlertingService()

    async def calculate_portfolio_heat(self, connection_id: int) -> dict[str, float]:
        """
        Calculate portfolio heat (total risk exposure).
        
        Portfolio heat = sum of (position_value * stop_loss_percent) / total_portfolio_value
        
        Returns:
            Dict with heat metrics
        """
        stmt = (
            select(Position, Strategy)
            .join(Strategy, Position.strategy_id == Strategy.id)
            .where(Strategy.exchange_connection_id == connection_id)
        )
        result = await self.db.execute(stmt)
        positions_data = result.all()

        if not positions_data:
            return {
                "total_heat": 0.0,
                "heat_percent": 0.0,
                "position_count": 0,
                "total_risk_usdt": 0.0,
            }

        total_portfolio_value = 0.0
        total_risk_usdt = 0.0
        position_count = 0

        for position, strategy in positions_data:
            if not position.current_price:
                continue

            position_value = position.amount * position.current_price
            total_portfolio_value += position_value

            if position.trailing_stop_enabled and position.trailing_stop_percent:
                risk_percent = position.trailing_stop_percent
            else:
                risk_percent = 2.0

            position_risk = position_value * (risk_percent / 100)
            total_risk_usdt += position_risk
            position_count += 1

        heat_percent = (total_risk_usdt / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0

        return {
            "total_heat": total_risk_usdt,
            "heat_percent": heat_percent,
            "position_count": position_count,
            "total_risk_usdt": total_risk_usdt,
            "total_portfolio_value": total_portfolio_value,
        }

    async def check_portfolio_heat_limit(self, connection_id: int, max_heat_percent: float = 10.0) -> dict[str, any]:
        """
        Check if portfolio heat exceeds limit.
        
        Args:
            connection_id: Exchange connection ID
            max_heat_percent: Maximum allowed heat percentage (default 10%)
        
        Returns:
            Dict with 'limit_exceeded' bool and 'current_heat' float
        """
        heat_data = await self.calculate_portfolio_heat(connection_id)
        limit_exceeded = heat_data["heat_percent"] > max_heat_percent

        if limit_exceeded:
            logger.warning(
                "Portfolio heat limit exceeded",
                connection_id=connection_id,
                current_heat=heat_data["heat_percent"],
                max_heat=max_heat_percent,
            )
            await self.alerting_service.alert_portfolio_heat_limit(
                connection_id=connection_id,
                current_heat=heat_data["heat_percent"],
                max_heat=max_heat_percent,
            )

        return {
            "limit_exceeded": limit_exceeded,
            "current_heat": heat_data["heat_percent"],
            "max_heat": max_heat_percent,
            "heat_data": heat_data,
        }

