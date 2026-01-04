"""Backtesting endpoints."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.backtest import Backtest
from app.workers.backtest_tasks import run_backtest_task

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/run")
async def run_backtest(
    strategy_id: int = Query(..., description="Strategy ID to backtest"),
    connection_id: int = Query(..., description="Exchange connection ID"),
    symbol: str = Query(..., description="Trading pair (e.g., BTC/USDT)"),
    start_date: str = Query(...,
                            description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(...,
                          description="End date (ISO format: YYYY-MM-DD)"),
    timeframe: str = Query("1h", description="Timeframe (1h, 4h, 1d)"),
    initial_balance: float = Query(
        10000.0, description="Starting balance in USDT"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a backtest on historical data (async via Celery).

    Returns immediately with backtest_id. Use /status/{backtest_id} to check progress.

    Example:
        POST /api/v1/backtest/run?strategy_id=1&connection_id=6&symbol=BTC/USDT&start_date=2024-01-01&end_date=2024-01-31&timeframe=1h&initial_balance=10000
    """
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        if start >= end:
            raise HTTPException(
                status_code=400, detail="start_date must be before end_date"
            )

        if (end - start).days > 365:
            raise HTTPException(
                status_code=400, detail="Backtest period cannot exceed 365 days"
            )

        # Create backtest record in database
        backtest_record = Backtest(
            strategy_id=strategy_id,
            connection_id=connection_id,
            symbol=symbol,
            start_date=start,
            end_date=end,
            timeframe=timeframe,
            initial_balance=Decimal(str(initial_balance)),
            initial_cash=Decimal(str(initial_balance)),
            final_balance=Decimal("0"),
            final_cash=Decimal("0"),
            total_pnl=Decimal("0"),
            total_pnl_percent=Decimal("0"),
            status="pending",
        )
        db.add(backtest_record)
        await db.flush()
        backtest_id = backtest_record.id
        await db.commit()

        # Trigger Celery task (non-blocking)
        run_backtest_task.delay(
            backtest_id=backtest_id,
            strategy_id=strategy_id,
            connection_id=connection_id,
            symbol=symbol,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            timeframe=timeframe,
            initial_balance=initial_balance,
        )

        return {
            "backtest_id": backtest_id,
            "status": "pending",
            "message": "Backtest started. Use /api/v1/backtest/status/{backtest_id} to check progress.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick")
async def quick_backtest(
    strategy_id: int = Query(..., description="Strategy ID to backtest"),
    connection_id: int = Query(..., description="Exchange connection ID"),
    symbol: str = Query(..., description="Trading pair (e.g., BTC/USDT)"),
    days: int = Query(
        30, description="Number of days to backtest (default: 30)"),
    timeframe: str = Query("1h", description="Timeframe (1h, 4h, 1d)"),
    initial_balance: float = Query(
        10000.0, description="Starting balance in USDT"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a quick backtest for the last N days (async via Celery).

    Returns immediately with backtest_id. Use /status/{backtest_id} to check progress.

    Example:
        GET /api/v1/backtest/quick?strategy_id=1&connection_id=6&symbol=BTC/USDT&days=30
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Create backtest record in database
        backtest_record = Backtest(
            strategy_id=strategy_id,
            connection_id=connection_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            initial_balance=Decimal(str(initial_balance)),
            initial_cash=Decimal(str(initial_balance)),
            final_balance=Decimal("0"),  # Will be updated when complete
            final_cash=Decimal("0"),
            total_pnl=Decimal("0"),
            total_pnl_percent=Decimal("0"),
            status="pending",
        )
        db.add(backtest_record)
        await db.flush()  # Get the ID
        backtest_id = backtest_record.id
        await db.commit()

        # Trigger Celery task (non-blocking)
        try:
            task_result = run_backtest_task.delay(
                backtest_id=backtest_id,
                strategy_id=strategy_id,
                connection_id=connection_id,
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                timeframe=timeframe,
                initial_balance=initial_balance,
            )
            logger.info(
                "Backtest task triggered",
                backtest_id=backtest_id,
                task_id=task_result.id,
            )
        except Exception as e:
            logger.error(
                "Failed to trigger backtest task",
                backtest_id=backtest_id,
                error=str(e),
            )
            # Update status to failed
            backtest_record.status = "failed"
            backtest_record.error_message = f"Failed to trigger task: {str(e)}"
            await db.commit()
            raise HTTPException(
                status_code=500, detail=f"Failed to trigger backtest: {str(e)}")

        return {
            "backtest_id": backtest_id,
            "status": "pending",
            "message": "Backtest started. Use /api/v1/backtest/status/{backtest_id} to check progress.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_backtests(
    strategy_id: Optional[int] = Query(
        None, description="Filter by strategy ID"),
    connection_id: Optional[int] = Query(
        None, description="Filter by connection ID"),
    limit: int = Query(
        50, description="Maximum number of backtests to return"),
    offset: int = Query(0, description="Number of backtests to skip"),
    db: AsyncSession = Depends(get_db),
):
    """List all backtests, optionally filtered by strategy or connection."""
    from sqlalchemy import select, desc
    from sqlalchemy.orm import selectinload

    stmt = select(Backtest).order_by(
        desc(Backtest.created_at)).offset(offset).limit(limit)

    if strategy_id:
        stmt = stmt.where(Backtest.strategy_id == strategy_id)
    if connection_id:
        stmt = stmt.where(Backtest.connection_id == connection_id)

    result = await db.execute(stmt)
    backtests = result.scalars().all()

    backtests_data = []
    for backtest in backtests:
        backtests_data.append({
            "backtest_id": backtest.id,
            "strategy_id": backtest.strategy_id,
            "connection_id": backtest.connection_id,
            "symbol": backtest.symbol,
            "start_date": backtest.start_date.isoformat(),
            "end_date": backtest.end_date.isoformat(),
            "timeframe": backtest.timeframe,
            "status": backtest.status,
            "created_at": backtest.created_at.isoformat(),
            "initial_balance": float(backtest.initial_balance),
            "final_balance": float(backtest.final_balance) if backtest.final_balance else None,
            "total_pnl": float(backtest.total_pnl) if backtest.total_pnl else None,
            "total_pnl_percent": float(backtest.total_pnl_percent) if backtest.total_pnl_percent else None,
            "total_trades": backtest.total_trades,
            "win_rate": float(backtest.win_rate) if backtest.win_rate else None,
            "error_message": backtest.error_message,
        })

    return {
        "backtests": backtests_data,
        "total": len(backtests_data),
    }


@router.get("/status/{backtest_id}")
async def get_backtest_status(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get backtest status and results."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(Backtest).options(selectinload(
        Backtest.trades)).where(Backtest.id == backtest_id)
    result = await db.execute(stmt)
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # If completed, return full results
    if backtest.status == "completed":
        # Load trades (already loaded via selectinload)
        trades_data = []
        for trade in backtest.trades:
            trades_data.append({
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": float(trade.entry_price),
                "exit_price": float(trade.exit_price) if trade.exit_price else None,
                "quantity": float(trade.quantity),
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                "pnl": float(trade.pnl) if trade.pnl else None,
                "pnl_percent": trade.pnl_percent,
                "status": trade.status,
            })

        return {
            "backtest_id": backtest.id,
            "status": backtest.status,
            "strategy_id": backtest.strategy_id,
            "connection_id": backtest.connection_id,
            "symbol": backtest.symbol,
            "start_date": backtest.start_date.isoformat(),
            "end_date": backtest.end_date.isoformat(),
            "timeframe": backtest.timeframe,
            "initial_balance": float(backtest.initial_balance),
            "final_balance": float(backtest.final_balance),
            "total_pnl": float(backtest.total_pnl),
            "total_pnl_percent": float(backtest.total_pnl_percent),
            "total_trades": backtest.total_trades,
            "winning_trades": backtest.winning_trades,
            "losing_trades": backtest.losing_trades,
            "win_rate": backtest.win_rate,
            "avg_win": backtest.avg_win,
            "avg_loss": backtest.avg_loss,
            "profit_factor": backtest.profit_factor,
            "max_drawdown": backtest.max_drawdown,
            "max_drawdown_percent": backtest.max_drawdown_percent,
            "sharpe_ratio": backtest.sharpe_ratio,
            "largest_win": backtest.largest_win,
            "largest_loss": backtest.largest_loss,
            "avg_trade_duration_hours": backtest.avg_trade_duration_hours,
            "trades": trades_data,
        }

    # If pending, running, cancelled, or failed, return basic info
    return {
        "backtest_id": backtest.id,
        "status": backtest.status,
        "strategy_id": backtest.strategy_id,
        "connection_id": backtest.connection_id,
        "symbol": backtest.symbol,
        "start_date": backtest.start_date.isoformat(),
        "end_date": backtest.end_date.isoformat(),
        "timeframe": backtest.timeframe,
        "initial_balance": float(backtest.initial_balance),
        "final_balance": float(backtest.final_balance) if backtest.final_balance else None,
        "total_pnl": float(backtest.total_pnl) if backtest.total_pnl else None,
        "total_pnl_percent": float(backtest.total_pnl_percent) if backtest.total_pnl_percent else None,
        "total_trades": backtest.total_trades,
        "win_rate": float(backtest.win_rate) if backtest.win_rate else None,
        "error_message": backtest.error_message,
    }


@router.post("/cancel/{backtest_id}")
async def cancel_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running backtest."""
    from sqlalchemy import select
    from app.workers.celery_app import celery_app

    stmt = select(Backtest).where(Backtest.id == backtest_id)
    result = await db.execute(stmt)
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if backtest.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel backtest with status: {backtest.status}"
        )

    # Try to revoke the Celery task
    # Note: We need to find the task ID. Since we don't store it, we'll check active tasks
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()

        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    # Check if this task is for our backtest_id
                    task_args = task.get('kwargs', {}) or task.get('args', [])
                    if isinstance(task_args, dict) and task_args.get('backtest_id') == backtest_id:
                        task_id = task['id']
                        celery_app.control.revoke(task_id, terminate=True)
                        logger.info("Backtest task revoked",
                                    backtest_id=backtest_id, task_id=task_id)
                        break
    except Exception as e:
        logger.warning("Could not revoke Celery task",
                       backtest_id=backtest_id, error=str(e))
        # Continue anyway - we'll still mark it as cancelled in the DB

    # Update status to cancelled
    backtest.status = "cancelled"
    backtest.error_message = "Cancelled by user"
    await db.commit()

    logger.info("Backtest cancelled", backtest_id=backtest_id)

    return {
        "backtest_id": backtest.id,
        "status": "cancelled",
        "message": "Backtest cancelled",
    }


@router.post("/retry/{backtest_id}")
async def retry_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retry a pending or failed backtest."""
    from sqlalchemy import select

    stmt = select(Backtest).where(Backtest.id == backtest_id)
    result = await db.execute(stmt)
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if backtest.status == "completed":
        raise HTTPException(
            status_code=400, detail="Backtest already completed")

    # Update status to pending and retrigger
    backtest.status = "pending"
    backtest.error_message = None
    await db.commit()

    # Trigger Celery task
    run_backtest_task.delay(
        backtest_id=backtest.id,
        strategy_id=backtest.strategy_id,
        connection_id=backtest.connection_id,
        symbol=backtest.symbol,
        start_date=backtest.start_date.isoformat(),
        end_date=backtest.end_date.isoformat(),
        timeframe=backtest.timeframe,
        initial_balance=float(backtest.initial_balance),
    )

    return {
        "backtest_id": backtest.id,
        "status": "pending",
        "message": "Backtest retriggered",
    }
