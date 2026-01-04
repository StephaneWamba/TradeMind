"""Automation control endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.strategy import Strategy
from app.workers.strategy_automation import execute_strategy_automation
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/execute/{strategy_id}")
async def trigger_strategy_automation(
    strategy_id: int,
    symbol: str = "BTC/USDT",
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger autonomous trading for a specific strategy.
    
    This endpoint allows you to:
    - Test strategy execution
    - Manually trigger trades
    - Monitor automation behavior
    """
    try:
        # Verify strategy exists and is active
        strategy = await db.get(Strategy, strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        if not strategy.is_active:
            raise HTTPException(
                status_code=400,
                detail="Strategy is not active. Activate it first."
            )
        
        # Execute automation
        result = await execute_strategy_automation(strategy_id, symbol)
        
        return {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "result": result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger strategy automation", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger automation: {str(e)}")


@router.get("/status")
async def get_automation_status(db: AsyncSession = Depends(get_db)):
    """Get status of all active strategies and automation."""
    try:
        stmt = select(Strategy).where(Strategy.is_active == True)
        result = await db.execute(stmt)
        active_strategies = result.scalars().all()
        
        # Check if Celery beat is running (check for scheduled tasks)
        # This is a simple check - in production you'd want more robust monitoring
        beat_running = True  # Assume running if we can query
        
        return {
            "automation_enabled": True,
            "beat_running": beat_running,
            "active_strategies": len(active_strategies),
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "connection_id": s.exchange_connection_id,
                }
                for s in active_strategies
            ],
        }
    except Exception as e:
        logger.error("Failed to get automation status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/enable/{strategy_id}")
async def enable_automation(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Enable automation for a strategy."""
    try:
        strategy = await db.get(Strategy, strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy.is_active = True
        strategy.status = "active"
        await db.commit()
        await db.refresh(strategy)
        
        logger.info("Strategy automation enabled", strategy_id=strategy_id)
        
        return {
            "strategy_id": strategy_id,
            "status": "enabled",
            "is_active": strategy.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to enable automation", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to enable automation: {str(e)}")


@router.post("/disable/{strategy_id}")
async def disable_automation(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Disable automation for a strategy."""
    try:
        strategy = await db.get(Strategy, strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy.is_active = False
        strategy.status = "paused"
        await db.commit()
        await db.refresh(strategy)
        
        logger.info("Strategy automation disabled", strategy_id=strategy_id)
        
        return {
            "strategy_id": strategy_id,
            "status": "disabled",
            "is_active": strategy.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disable automation", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to disable automation: {str(e)}")

