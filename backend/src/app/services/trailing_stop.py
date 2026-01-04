"""Trailing stop-loss management service."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Position
from app.models.trade import Order
from app.services.orders import OrderService

logger = structlog.get_logger(__name__)


class TrailingStopService:
    """Service for managing trailing stop-loss orders."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_service = OrderService(db)

    async def update_trailing_stops(self, connection_id: int):
        """
        Update all trailing stop-loss orders based on current prices.

        This should be called periodically (e.g., every price update).
        """
        # Get all positions with trailing stops enabled
        stmt = select(Position).where(Position.trailing_stop_enabled == True)
        result = await self.db.execute(stmt)
        positions = result.scalars().all()

        for position in positions:
            if not position.current_price or not position.trailing_stop_percent:
                continue

            # Calculate new trailing stop price
            # Trailing stop follows price up but not down
            new_trailing_price = position.current_price * \
                (1 - position.trailing_stop_percent / 100)

            # Only update if price moved up (trailing stop only moves up)
            if position.trailing_stop_trigger_price is None:
                # First time - set initial trigger
                position.trailing_stop_trigger_price = position.current_price
            elif position.current_price > position.trailing_stop_trigger_price:
                # Price moved up - update trailing stop
                position.trailing_stop_trigger_price = position.current_price

                # Cancel old stop-loss order
                if position.stop_loss_order_id:
                    try:
                        old_order = await self.db.get(Order, position.stop_loss_order_id)
                        if old_order and old_order.status == "pending":
                            # Cancel on exchange
                            from app.services.exchange import ExchangeService
                            exchange_service = ExchangeService(self.db)
                            client = await exchange_service.get_client(connection_id)
                            await client.cancel_order(old_order.exchange_order_id, position.symbol)
                            old_order.status = "cancelled"
                    except Exception as e:
                        logger.warning(
                            "Failed to cancel old trailing stop", position_id=position.id, error=str(e))

                # Place new stop-loss order at trailing price
                try:
                    stop_order = await self.order_service.place_stop_market_order(
                        connection_id=connection_id,
                        symbol=position.symbol,
                        side="sell",
                        amount=position.amount,
                        stop_price=new_trailing_price,
                        strategy_id=position.strategy_id,
                    )
                    position.stop_loss_order_id = stop_order.get("db_id")
                    logger.info(
                        "Trailing stop updated",
                        position_id=position.id,
                        old_price=position.trailing_stop_trigger_price,
                        new_price=new_trailing_price,
                    )
                except Exception as e:
                    logger.error("Failed to update trailing stop",
                                 position_id=position.id, error=str(e))

        await self.db.commit()

    async def enable_trailing_stop(
        self,
        position_id: int,
        trailing_percent: float,
        connection_id: int,
    ) -> bool:
        """Enable trailing stop-loss for a position."""
        position = await self.db.get(Position, position_id)
        if not position:
            return False

        position.trailing_stop_enabled = True
        position.trailing_stop_percent = trailing_percent
        position.trailing_stop_trigger_price = position.current_price or position.entry_price

        # Place initial trailing stop order
        if position.current_price:
            trailing_price = position.current_price * \
                (1 - trailing_percent / 100)
            try:
                stop_order = await self.order_service.place_stop_market_order(
                    connection_id=connection_id,
                    symbol=position.symbol,
                    side="sell",
                    amount=position.amount,
                    stop_price=trailing_price,
                    strategy_id=position.strategy_id,
                )
                position.stop_loss_order_id = stop_order.get("db_id")
            except Exception as e:
                logger.error("Failed to enable trailing stop",
                             position_id=position_id, error=str(e))
                return False

        await self.db.commit()
        return True
