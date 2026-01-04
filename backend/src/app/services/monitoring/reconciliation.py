"""Order reconciliation service - sync database with exchange state."""

import structlog
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Order
from app.models.strategy import Strategy
from app.services.exchange import ExchangeService
from app.services.notification.alerting import AlertingService
from app.core.events import event_bus

logger = structlog.get_logger(__name__)


class OrderReconciliationService:
    """Service for reconciling orders between database and exchange."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)
        self.alerting_service = AlertingService()

    async def reconcile_orders(self, connection_id: int) -> dict[str, any]:
        """
        Reconcile orders between database and exchange.
        
        Returns:
            Dict with reconciliation results
        """
        discrepancies = []
        fixed_orders = 0
        client = None
        
        try:
            stmt = (
                select(Order, Strategy)
                .join(Strategy, Order.strategy_id == Strategy.id)
                .where(
                    Strategy.exchange_connection_id == connection_id,
                    Order.status.in_(["pending", "filled"]),
                )
            )
            result = await self.db.execute(stmt)
            orders_data = result.all()

            if not orders_data:
                return {
                    "connection_id": connection_id,
                    "orders_checked": 0,
                    "discrepancies": 0,
                    "fixed": 0,
                }

            client = await self.exchange_service.get_client(connection_id)

            for order, strategy in orders_data:
                try:
                    exchange_status = await client.get_order_status(
                        order.exchange_order_id, order.symbol
                    )

                    db_status = order.status
                    exchange_status_str = exchange_status.get("status", "").lower()

                    if exchange_status_str in ["filled", "closed", "done"]:
                        exchange_status_str = "filled"
                    elif exchange_status_str in ["cancelled", "canceled"]:
                        exchange_status_str = "cancelled"
                    elif exchange_status_str in ["pending", "new", "open"]:
                        exchange_status_str = "pending"
                    else:
                        exchange_status_str = "unknown"

                    if db_status != exchange_status_str:
                        discrepancy = {
                            "order_id": order.id,
                            "symbol": order.symbol,
                            "db_status": db_status,
                            "exchange_status": exchange_status_str,
                        }
                        discrepancies.append(discrepancy)

                        order.status = exchange_status_str
                        order.filled_amount = exchange_status.get("filled", order.filled_amount)
                        order.filled_price = exchange_status.get("price", order.filled_price)
                        fixed_orders += 1

                        logger.warning(
                            "Order status discrepancy fixed",
                            order_id=order.id,
                            db_status=db_status,
                            exchange_status=exchange_status_str,
                        )

                except Exception as e:
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["not found", "does not exist", "invalid"]):
                        if order.status == "pending":
                            order.status = "cancelled"
                            fixed_orders += 1
                            logger.info(
                                "Order not found on exchange, marked as cancelled",
                                order_id=order.id,
                            )
                    else:
                        logger.warning(
                            "Error checking order status",
                            order_id=order.id,
                            error=str(e),
                        )

            await self.db.commit()

            if len(discrepancies) > 5:
                await self.alerting_service.send_alert(
                    subject=f"Order Reconciliation: {len(discrepancies)} Discrepancies Found",
                    message=f"""
                    <h3>Order Reconciliation Report</h3>
                    <p><strong>Connection ID:</strong> {connection_id}</p>
                    <p><strong>Orders Checked:</strong> {len(orders_data)}</p>
                    <p><strong>Discrepancies Found:</strong> {len(discrepancies)}</p>
                    <p><strong>Orders Fixed:</strong> {fixed_orders}</p>
                    <p style="color: #ffc107;"><strong>Note:</strong> Please review the order statuses.</p>
                    """,
                    priority="high",
                )

            return {
                "connection_id": connection_id,
                "orders_checked": len(orders_data),
                "discrepancies": len(discrepancies),
                "fixed": fixed_orders,
                "discrepancy_details": discrepancies,
            }

        except Exception as e:
            logger.error("Order reconciliation failed", connection_id=connection_id, error=str(e))
            raise
        finally:
            if client:
                try:
                    await client.close()
                except:
                    pass

    async def find_orphaned_orders(self, connection_id: int) -> list[dict]:
        """Find orders in database that don't exist on exchange."""
        orphaned = []
        client = None
        
        try:
            stmt = (
                select(Order, Strategy)
                .join(Strategy, Order.strategy_id == Strategy.id)
                .where(
                    Strategy.exchange_connection_id == connection_id,
                    Order.status == "pending",
                )
            )
            result = await self.db.execute(stmt)
            orders_data = result.all()

            client = await self.exchange_service.get_client(connection_id)

            for order, strategy in orders_data:
                try:
                    await client.get_order_status(order.exchange_order_id, order.symbol)
                except Exception as e:
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["not found", "does not exist", "invalid"]):
                        orphaned.append({
                            "order_id": order.id,
                            "exchange_order_id": order.exchange_order_id,
                            "symbol": order.symbol,
                            "created_at": order.created_at.isoformat() if order.created_at else None,
                        })

            return orphaned

        except Exception as e:
            logger.error("Error finding orphaned orders", connection_id=connection_id, error=str(e))
            return orphaned
        finally:
            if client:
                try:
                    await client.close()
                except:
                    pass

