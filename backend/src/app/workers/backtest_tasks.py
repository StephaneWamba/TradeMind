"""Celery tasks for backtesting operations."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import structlog
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.domain.backtest.engine import BacktestService
from app.services.exchange import ExchangeService
from app.models.backtest import Backtest, BacktestTrade

logger = structlog.get_logger(__name__)


# Global event loop per worker process (persists across tasks)
_worker_event_loop = None


def _get_or_create_loop():
    """Get or create persistent event loop for this worker process."""
    global _worker_event_loop

    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            _worker_event_loop = loop
            return loop
    except RuntimeError:
        pass

    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)

    return _worker_event_loop


def _run_async(coro):
    """Run async coroutine in worker's persistent event loop."""
    loop = _get_or_create_loop()
    return loop.run_until_complete(coro)


@celery_app.task(name="run_backtest", bind=True, max_retries=3, time_limit=3600)  # 1 hour for backtests
def run_backtest_task(
    self,
    backtest_id: int,
    strategy_id: int,
    connection_id: int,
    symbol: str,
    start_date: str,  # ISO format string
    end_date: str,  # ISO format string
    timeframe: str,
    initial_balance: float,
):
    """
    Run a backtest in the background.
    
    This task:
    1. Fetches exchange credentials (short DB session)
    2. Runs backtest without holding DB session
    3. Saves results to database (short DB session)
    """
    logger.info(
        "Backtest task received",
        backtest_id=backtest_id,
        strategy_id=strategy_id,
        symbol=symbol,
        task_id=self.request.id,
    )
    
    async def _run():
        # Step 1: Fetch exchange client (short-lived session)
        client = None
        async with AsyncSessionLocal() as db:
            try:
                exchange_service = ExchangeService(db)
                client = await exchange_service.get_client(connection_id)
                # Update backtest status to "running"
                stmt = select(Backtest).where(Backtest.id == backtest_id)
                result = await db.execute(stmt)
                backtest_record = result.scalar_one_or_none()
                if backtest_record:
                    backtest_record.status = "running"
                    await db.commit()
            except Exception as e:
                logger.error("Failed to fetch exchange client for backtest", 
                           backtest_id=backtest_id, error=str(e))
                # Update status to failed
                async with AsyncSessionLocal() as db2:
                    stmt = select(Backtest).where(Backtest.id == backtest_id)
                    result = await db2.execute(stmt)
                    backtest_record = result.scalar_one_or_none()
                    if backtest_record:
                        backtest_record.status = "failed"
                        backtest_record.error_message = f"Failed to fetch exchange client: {str(e)}"
                        await db2.commit()
                raise

        # Step 2: Run backtest (NO DB SESSION HELD)
        try:
            # Parse dates
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            # Create backtest service with a session
            # Since we pass pre_fetched_client, the service won't query DB during execution
            # The session will be closed when the context exits
            async with AsyncSessionLocal() as db:
                backtest_service = BacktestService(db)
                # Run backtest with pre-fetched client (no DB queries during execution)
                backtest_results = await backtest_service.run_backtest(
                    strategy_id=strategy_id,
                    connection_id=connection_id,
                    symbol=symbol,
                    start_date=start,
                    end_date=end,
                    timeframe=timeframe,
                    initial_balance=initial_balance,
                    pre_fetched_client=client,
                )
                # Session will be closed here when exiting the context
            # Session released here - backtest runs without holding DB connection

        except Exception as e:
            logger.error("Backtest execution failed", 
                        backtest_id=backtest_id, error=str(e))
            # Update status to failed
            async with AsyncSessionLocal() as db:
                stmt = select(Backtest).where(Backtest.id == backtest_id)
                query_result = await db.execute(stmt)
                backtest_record = query_result.scalar_one_or_none()
                if backtest_record:
                    backtest_record.status = "failed"
                    backtest_record.error_message = str(e)
                    await db.commit()
            raise

        # Step 3: Save results to database (short-lived session)
        async with AsyncSessionLocal() as db:
            try:
                stmt = select(Backtest).where(Backtest.id == backtest_id)
                query_result = await db.execute(stmt)
                backtest_record = query_result.scalar_one_or_none()

                if not backtest_record:
                    logger.error("Backtest record not found", backtest_id=backtest_id)
                    return

                # Update backtest record with results
                backtest_record.final_balance = Decimal(str(backtest_results.get("final_balance", 0)))
                backtest_record.final_cash = Decimal(str(backtest_results.get("final_cash", backtest_results.get("final_balance", 0))))
                backtest_record.total_pnl = Decimal(str(backtest_results.get("total_pnl", 0)))
                backtest_record.total_pnl_percent = Decimal(str(backtest_results.get("total_pnl_percent", 0)))
                backtest_record.total_trades = backtest_results.get("total_trades", 0)
                backtest_record.winning_trades = backtest_results.get("winning_trades", 0)
                backtest_record.losing_trades = backtest_results.get("losing_trades", 0)
                backtest_record.win_rate = backtest_results.get("win_rate")
                backtest_record.avg_win = backtest_results.get("avg_win")
                backtest_record.avg_loss = backtest_results.get("avg_loss")
                backtest_record.profit_factor = backtest_results.get("profit_factor")
                backtest_record.max_drawdown = backtest_results.get("max_drawdown")
                backtest_record.max_drawdown_percent = backtest_results.get("max_drawdown_percent")
                backtest_record.sharpe_ratio = backtest_results.get("sharpe_ratio")
                backtest_record.largest_win = backtest_results.get("largest_win")
                backtest_record.largest_loss = backtest_results.get("largest_loss")
                backtest_record.avg_trade_duration_hours = backtest_results.get("avg_trade_duration_hours")
                backtest_record.status = "completed"

                # Save trades
                if backtest_results.get("trades"):
                    for trade_data in backtest_results["trades"]:
                        trade = BacktestTrade(
                            backtest_id=backtest_id,
                            symbol=trade_data.get("symbol", symbol),
                            side=trade_data.get("side", "BUY"),
                            entry_price=Decimal(str(trade_data.get("entry_price", 0))),
                            exit_price=Decimal(str(trade_data.get("exit_price", 0))) if trade_data.get("exit_price") else None,
                            quantity=Decimal(str(trade_data.get("quantity", 0))),
                            entry_time=datetime.fromisoformat(trade_data["entry_time"].replace("Z", "+00:00")) if isinstance(trade_data.get("entry_time"), str) else trade_data.get("entry_time"),
                            exit_time=datetime.fromisoformat(trade_data["exit_time"].replace("Z", "+00:00")) if isinstance(trade_data.get("exit_time"), str) and trade_data.get("exit_time") else None,
                            pnl=Decimal(str(trade_data.get("pnl", 0))) if trade_data.get("pnl") else None,
                            pnl_percent=trade_data.get("pnl_percent"),
                            stop_loss=Decimal(str(trade_data.get("stop_loss", 0))) if trade_data.get("stop_loss") else None,
                            take_profit=Decimal(str(trade_data.get("take_profit", 0))) if trade_data.get("take_profit") else None,
                            status=trade_data.get("status", "closed"),
                        )
                        db.add(trade)

                await db.commit()
                logger.info("Backtest completed and saved", backtest_id=backtest_id)

            except Exception as e:
                logger.error("Failed to save backtest results", 
                           backtest_id=backtest_id, error=str(e))
                await db.rollback()
                raise

        # Close exchange client
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.warning("Error closing exchange client", error=str(e))

    _run_async(_run())

