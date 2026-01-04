"""Background tasks for price updates and portfolio calculations."""

import asyncio
import sys
from typing import List
import structlog
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.events import event_bus
from app.services.market import MarketDataService
from app.domain.trading.position import PositionService
from app.services.portfolio import PortfolioService
from app.services.monitoring.order_monitor import OrderMonitorService
from app.services.monitoring.reconciliation import OrderReconciliationService
from app.models.portfolio import Position
from app.models.strategy import Strategy
from app.models.trade import Order

logger = structlog.get_logger(__name__)


# Global event loop per worker process (persists across tasks)
_worker_event_loop = None


def _get_or_create_loop():
    """Get or create persistent event loop for this worker process."""
    global _worker_event_loop

    # Try to get existing loop
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            _worker_event_loop = loop
            return loop
    except RuntimeError:
        pass

    # Create new loop if needed (persists for worker lifetime)
    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)

    return _worker_event_loop


def _run_async(coro):
    """Run async coroutine in worker's persistent event loop."""
    # Use persistent event loop per worker process
    # This avoids issues with database connections tied to specific loops
    # The loop persists for the entire worker process lifetime
    loop = _get_or_create_loop()

    # Run the coroutine in the existing loop
    # Don't close the loop - it will be reused for next task
    return loop.run_until_complete(coro)


@celery_app.task(name="update_prices")
def update_prices_task(connection_id: int):
    """Update prices for all positions in a connection."""
    async def _update():
        # Initialize event bus in this event loop
        await event_bus.initialize()

        # Create a fresh database session in this event loop
        async with AsyncSessionLocal() as db:
            try:
                market_service = MarketDataService(db)
                position_service = PositionService(db)

                # Get all positions for this connection via strategy
                stmt = select(Position).join(
                    Strategy, Position.strategy_id == Strategy.id
                ).where(Strategy.exchange_connection_id == connection_id)
                result = await db.execute(stmt)
                positions = result.scalars().all()

                if not positions:
                    return

                # Get unique symbols
                symbols = list(set(pos.symbol for pos in positions))

                # Fetch prices
                tickers = await market_service.get_tickers(connection_id, symbols)

                # Emit price update events
                for ticker in tickers:
                    if not ticker:
                        continue

                    symbol = ticker.get("symbol", "").replace("/", "")
                    price = float(ticker.get("last", 0)
                                  or ticker.get("price", 0))
                    change_24h = ticker.get("percentage", 0)
                    volume_24h = ticker.get("quoteVolume", 0)

                    await event_bus.emit(
                        "price.updated",
                        connection_id=connection_id,
                        data={
                            "symbol": symbol,
                            "price": price,
                            "change_24h": change_24h,
                            "volume_24h": volume_24h,
                        }
                    )

                # Update position prices
                await position_service.update_position_prices(connection_id)

                # Update trailing stops (if any positions have trailing stops enabled)
                from app.services.trailing_stop import TrailingStopService
                trailing_service = TrailingStopService(db)
                await trailing_service.update_trailing_stops(connection_id)

            except Exception as e:
                logger.error("Error in price update task",
                             connection_id=connection_id, error=str(e))
                raise

    # Run async function with proper event loop management
    _run_async(_update())


@celery_app.task(name="update_portfolio")
def update_portfolio_task(connection_id: int):
    """Update portfolio value and broadcast."""
    async def _update():
        # Initialize event bus in this event loop
        await event_bus.initialize()

        # Create a fresh database session in this event loop
        async with AsyncSessionLocal() as db:
            try:
                portfolio_service = PortfolioService(db)
                portfolio_data = await portfolio_service.calculate_portfolio_value(connection_id)

                await event_bus.emit(
                    "portfolio.updated",
                    connection_id=connection_id,
                    data={
                        "total_value_usdt": portfolio_data.get("total_value_usdt", 0.0),
                        "cash_usdt": portfolio_data.get("cash_usdt", 0.0),
                        "invested_usdt": portfolio_data.get("invested_usdt", 0.0),
                        "unrealized_pnl": portfolio_data.get("unrealized_pnl", 0.0),
                        "unrealized_pnl_percent": portfolio_data.get("unrealized_pnl_percent", 0.0),
                        "daily_pnl": portfolio_data.get("daily_pnl", 0.0),
                        "daily_pnl_percent": portfolio_data.get("daily_pnl_percent", 0.0),
                    }
                )

            except Exception as e:
                logger.error("Error in portfolio update task",
                             connection_id=connection_id, error=str(e))
                raise

    # Run async function with proper event loop management
    _run_async(_update())


@celery_app.task(name="monitor_orders")
def monitor_orders_task(connection_id: int):
    """Monitor pending orders and update their status."""
    async def _monitor():
        await event_bus.initialize()

        async with AsyncSessionLocal() as db:
            try:
                order_monitor = OrderMonitorService(db)

                # Get all pending orders for this connection
                stmt = select(Order).join(
                    Strategy, Order.strategy_id == Strategy.id
                ).where(
                    Strategy.exchange_connection_id == connection_id,
                    Order.status == "pending"
                )
                result = await db.execute(stmt)
                pending_orders = result.scalars().all()

                for order in pending_orders:
                    await order_monitor.check_order_status(connection_id, order.id)

            except Exception as e:
                logger.error("Error in order monitoring task",
                             connection_id=connection_id, error=str(e))

    _run_async(_monitor())


@celery_app.task(name="reconcile_orders")
def reconcile_orders_task(connection_id: int):
    """Reconcile orders between database and exchange."""
    async def _reconcile():
        await event_bus.initialize()

        async with AsyncSessionLocal() as db:
            try:
                reconciliation_service = OrderReconciliationService(db)
                result = await reconciliation_service.reconcile_orders(connection_id)
                logger.info("Order reconciliation completed", **result)
            except Exception as e:
                logger.error("Error in order reconciliation task",
                             connection_id=connection_id, error=str(e))

    _run_async(_reconcile())


@celery_app.task(name="periodic_price_updates")
def periodic_price_updates_task(connection_ids: List[int]):
    """Periodic price updates for multiple connections."""
    for connection_id in connection_ids:
        update_prices_task.delay(connection_id)


@celery_app.task(name="autonomous_trading")
def autonomous_trading_task():
    """Periodic autonomous trading execution for all active strategies."""
    async def _run():
        await event_bus.initialize()
        from app.workers.strategy_automation import run_automation_for_all_active_strategies
        await run_automation_for_all_active_strategies()

    _run_async(_run())
