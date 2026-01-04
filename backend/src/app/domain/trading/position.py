"""Position tracking domain logic."""

from typing import Optional
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Position
from app.models.strategy import Strategy
from app.services.exchange import ExchangeService

logger = structlog.get_logger(__name__)


class PositionService:
    """Service for tracking and updating positions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)

    async def update_position_prices(self, connection_id: int):
        """Update current prices and unrealized P&L for all open positions."""
        stmt = select(Position)
        result = await self.db.execute(stmt)
        positions = result.scalars().all()

        for position in positions:
            client = None
            try:
                client = await self.exchange_service.get_client(connection_id)
                ticker = await client.get_ticker(position.symbol)
                current_price = ticker.get("price", position.current_price)

                unrealized_pnl = (
                    current_price - position.entry_price) * position.amount
                unrealized_pnl_percent = (
                    (current_price - position.entry_price) /
                    position.entry_price * 100
                    if position.entry_price > 0
                    else 0
                )

                position.current_price = current_price
                position.unrealized_pnl = unrealized_pnl
                position.unrealized_pnl_percent = unrealized_pnl_percent

                await self.db.commit()
            except Exception as e:
                logger.error(
                    "Failed to update position price",
                    position_id=position.id,
                    symbol=position.symbol,
                    error=str(e),
                )
                await self.db.rollback()
            finally:
                if client:
                    try:
                        await client.close()
                    except Exception as e:
                        logger.warning("Error closing exchange client", error=str(e))

    async def get_positions(
        self, connection_id: Optional[int] = None
    ) -> list[Position]:
        """
        Get all positions, optionally filtered by connection_id.
        
        Args:
            connection_id: Optional connection ID to filter by
            
        Returns:
            List of Position objects
        """
        if connection_id:
            stmt = (
                select(Position)
                .join(Strategy, Position.strategy_id == Strategy.id)
                .where(Strategy.connection_id == connection_id)
            )
        else:
            stmt = select(Position)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

