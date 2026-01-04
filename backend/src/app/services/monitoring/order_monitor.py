"""Order status monitoring service with retry logic."""

import asyncio
import time
from typing import Optional
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Order
from app.services.exchange import ExchangeService

logger = structlog.get_logger(__name__)


class OrderMonitorService:
    """Service for monitoring order status with retry logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)
        self.max_retries = 3
        self.retry_delays = [1.0, 2.0, 5.0]

    async def check_order_status(
        self, connection_id: int, order_id: int, retry_count: int = 0
    ) -> dict:
        """
        Check order status with retry logic.
        
        Args:
            connection_id: Exchange connection ID
            order_id: Database order ID
            retry_count: Current retry attempt
        
        Returns:
            Order status information
        """
        try:
            stmt = select(Order).where(Order.id == order_id)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                return {"error": "Order not found"}
            
            if order.status in ["filled", "cancelled", "failed"]:
                return {
                    "order_id": order.id,
                    "status": order.status,
                    "filled_amount": order.filled_amount,
                    "filled_price": order.filled_price,
                }
            
            client = await self.exchange_service.get_client(connection_id)
            exchange_status = await client.get_order_status(
                order.exchange_order_id, order.symbol
            )
            
            order.status = exchange_status.get("status", order.status)
            order.filled_amount = exchange_status.get("filled", order.filled_amount)
            order.filled_price = exchange_status.get("price", order.filled_price)
            
            await self.db.commit()
            await self.db.refresh(order)
            
            return {
                "order_id": order.id,
                "status": order.status,
                "filled_amount": order.filled_amount,
                "filled_price": order.filled_price,
            }
            
        except Exception as e:
            logger.warning(
                "Order status check failed",
                order_id=order_id,
                retry_count=retry_count,
                error=str(e),
            )
            
            if retry_count < self.max_retries:
                delay = self.retry_delays[retry_count]
                await asyncio.sleep(delay)
                return await self.check_order_status(connection_id, order_id, retry_count + 1)
            
            logger.error(
                "Order status check failed after max retries",
                order_id=order_id,
                error=str(e),
            )
            return {"error": str(e), "retries_exhausted": True}

    async def monitor_pending_orders(self, connection_id: int, interval_seconds: int = 5):
        """
        Continuously monitor pending orders.
        
        Args:
            connection_id: Exchange connection ID
            interval_seconds: Check interval in seconds
        """
        while True:
            try:
                stmt = select(Order).where(Order.status == "pending")
                result = await self.db.execute(stmt)
                pending_orders = result.scalars().all()
                
                for order in pending_orders:
                    await self.check_order_status(connection_id, order.id)
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error("Error in order monitoring loop", error=str(e))
                await asyncio.sleep(interval_seconds)

