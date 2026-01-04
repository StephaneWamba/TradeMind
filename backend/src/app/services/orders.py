"""Order service for placing and managing orders with accuracy and low latency."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Order
from app.services.exchange import ExchangeService

logger = structlog.get_logger(__name__)


class OrderService:
    """Service for order operations with accuracy and low latency."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)

    async def place_market_order(
        self, connection_id: int, symbol: str, side: str, amount: float, strategy_id: int = 1
    ) -> dict:
        """Place a market order with validation and low latency."""
        # Validate inputs for accuracy
        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)

            # Place order
            order_result = await client.place_market_order(symbol, side, amount)

            # Store order in database
            order = Order(
                exchange_order_id=order_result.get("id"),
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                order_type="market",
                amount=amount,
                price=None,  # Market orders don't have price
                status=order_result.get("status", "pending"),
                filled_amount=order_result.get("filled", 0.0),
                filled_price=order_result.get("price"),
                fee=order_result.get("fee", {}).get("cost") if isinstance(
                    order_result.get("fee"), dict) else None,
            )
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            logger.info(
                "Market order placed",
                connection_id=connection_id,
                symbol=symbol,
                side=side,
                amount=amount,
                order_id=order_result.get("id"),
                db_order_id=order.id,
            )

            return {**order_result, "db_id": order.id}
        except Exception as e:
            # Mark order as failed if it was created
            if 'order' in locals() and order:
                try:
                    order.status = "failed"
                    await self.db.commit()
                except:
                    pass
            raise
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))

    async def place_stop_market_order(
        self, connection_id: int, symbol: str, side: str, amount: float, stop_price: float, strategy_id: int = 1
    ) -> dict:
        """Place a stop-market order (for stop-loss)."""
        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if stop_price <= 0:
            raise ValueError("Stop price must be positive")

        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            order_result = await client.place_stop_market_order(symbol, side, amount, stop_price)

            order = Order(
                exchange_order_id=order_result.get("id"),
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                order_type="stop_market",
                amount=amount,
                price=stop_price,  # Store stop_price
                status=order_result.get("status", "pending"),
                filled_amount=order_result.get("filled", 0.0),
                filled_price=order_result.get("price"),
            )
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            logger.info(
                "Stop-market order placed",
                connection_id=connection_id,
                symbol=symbol,
                side=side,
                amount=amount,
                stop_price=stop_price,
                order_id=order_result.get("id"),
                db_order_id=order.id,
            )

            return {**order_result, "db_id": order.id}
        finally:
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))

    async def place_limit_order(
        self, connection_id: int, symbol: str, side: str, amount: float, price: float, strategy_id: int = 1
    ) -> dict:
        """Place a limit order with validation."""
        # Validate inputs for accuracy
        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if price <= 0:
            raise ValueError("Price must be positive")

        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)

            # Place order
            order_result = await client.place_limit_order(symbol, side, amount, price)

            # Store order in database
            order = Order(
                exchange_order_id=order_result.get("id"),
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                order_type="limit",
                amount=amount,
                price=price,
                status=order_result.get("status", "pending"),
                filled_amount=order_result.get("filled", 0.0),
                filled_price=order_result.get("price"),
                fee=order_result.get("fee", {}).get("cost") if isinstance(
                    order_result.get("fee"), dict) else None,
            )
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            logger.info(
                "Limit order placed",
                connection_id=connection_id,
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_id=order_result.get("id"),
                db_order_id=order.id,
            )

            return {**order_result, "db_id": order.id}
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))

    async def get_order_status(self, connection_id: int, order_id: str, symbol: str) -> dict:
        """Get order status."""
        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            status = await client.get_order_status(order_id, symbol)
            return status
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))

    async def place_oco_order(
        self,
        connection_id: int,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        limit_price: float,
        strategy_id: int = 1,
    ) -> dict:
        """Place an OCO (One-Cancels-Other) order - stop-loss + take-profit."""
        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if stop_price <= 0 or limit_price <= 0:
            raise ValueError("Stop price and limit price must be positive")

        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            order_result = await client.place_oco_order(symbol, side, amount, stop_price, limit_price)

            # OCO orders create multiple orders - store them
            oco_group_id = order_result.get("id")
            orders_in_group = order_result.get("orders", [])

            # Create order records for each order in the OCO group
            db_orders = []
            for oco_order in orders_in_group:
                order = Order(
                    exchange_order_id=oco_order.get("orderId"),
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side=side,
                    order_type="oco",
                    amount=amount,
                    price=limit_price if oco_order.get(
                        "type") == "LIMIT" else stop_price,
                    status=oco_order.get("status", "pending"),
                    oco_group_id=oco_group_id,
                )
                self.db.add(order)
                db_orders.append(order)

            await self.db.commit()
            for order in db_orders:
                await self.db.refresh(order)

            logger.info(
                "OCO order placed",
                connection_id=connection_id,
                symbol=symbol,
                side=side,
                amount=amount,
                stop_price=stop_price,
                limit_price=limit_price,
                oco_group_id=oco_group_id,
                orders_count=len(db_orders),
            )

            return {
                **order_result,
                "db_orders": [o.id for o in db_orders],
            }
        finally:
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))

    async def cancel_order(self, connection_id: int, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            result = await client.cancel_order(order_id, symbol)
            return result
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(
                        "Error closing exchange client", error=str(e))
