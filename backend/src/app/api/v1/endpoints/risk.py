"""Risk management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.core.database import get_db
from app.domain.risk.management import RiskManagementService

router = APIRouter()
logger = structlog.get_logger(__name__)


class RiskConfigUpdate(BaseModel):
    """Schema for updating risk configuration."""

    max_position_size_percent: float = Field(None, ge=0.0, le=0.10, description="Max position size (0-10%)")
    max_daily_loss_percent: float = Field(None, ge=0.0, le=0.20, description="Max daily loss (0-20%)")
    max_drawdown_percent: float = Field(None, ge=0.0, le=0.50, description="Max drawdown (0-50%)")
    min_confidence_threshold: float = Field(None, ge=0.0, le=1.0, description="Min confidence threshold (0-1)")
    position_sizing_method: str = Field(None, description="Position sizing method (fixed, kelly)")


@router.get("/config/{strategy_id}")
async def get_risk_config(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get risk configuration for a strategy."""
    risk_service = RiskManagementService(db)
    risk_config = await risk_service.get_risk_config(strategy_id)
    
    return {
        "strategy_id": risk_config.strategy_id,
        "max_position_size_percent": risk_config.max_position_size_percent,
        "max_daily_loss_percent": risk_config.max_daily_loss_percent,
        "max_drawdown_percent": risk_config.max_drawdown_percent,
        "min_confidence_threshold": risk_config.min_confidence_threshold,
        "position_sizing_method": risk_config.position_sizing_method,
        "emergency_stop": risk_config.emergency_stop,
    }


@router.put("/config/{strategy_id}")
async def update_risk_config(
    strategy_id: int,
    config: RiskConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update risk configuration for a strategy."""
    risk_service = RiskManagementService(db)
    
    risk_config = await risk_service.update_risk_config(
        strategy_id=strategy_id,
        max_position_size_percent=config.max_position_size_percent,
        max_daily_loss_percent=config.max_daily_loss_percent,
        max_drawdown_percent=config.max_drawdown_percent,
        min_confidence_threshold=config.min_confidence_threshold,
        position_sizing_method=config.position_sizing_method,
    )
    
    return {
        "strategy_id": risk_config.strategy_id,
        "max_position_size_percent": risk_config.max_position_size_percent,
        "max_daily_loss_percent": risk_config.max_daily_loss_percent,
        "max_drawdown_percent": risk_config.max_drawdown_percent,
        "min_confidence_threshold": risk_config.min_confidence_threshold,
        "position_sizing_method": risk_config.position_sizing_method,
        "emergency_stop": risk_config.emergency_stop,
    }


@router.get("/daily-loss/{strategy_id}")
async def get_daily_loss(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get daily loss status for a strategy."""
    risk_service = RiskManagementService(db)
    loss_status = await risk_service.check_daily_loss_limit(strategy_id)
    
    return loss_status


@router.get("/circuit-breaker/{strategy_id}")
async def get_circuit_breaker_status(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get circuit breaker status for a strategy."""
    risk_service = RiskManagementService(db)
    is_triggered = await risk_service.check_circuit_breaker(strategy_id)
    
    return {
        "strategy_id": strategy_id,
        "is_triggered": is_triggered,
    }


@router.post("/circuit-breaker/{strategy_id}/reset")
async def reset_circuit_breaker(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Reset circuit breaker for a strategy."""
    risk_service = RiskManagementService(db)
    await risk_service.reset_circuit_breaker(strategy_id)
    
    return {"message": "Circuit breaker reset", "strategy_id": strategy_id}


@router.post("/emergency-stop")
async def emergency_stop(
    strategy_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Emergency stop - pause all strategies or a specific strategy.
    
    Args:
        strategy_id: Optional strategy ID. If not provided, stops all strategies.
    """
    risk_service = RiskManagementService(db)
    await risk_service.emergency_stop(strategy_id)
    
    if strategy_id:
        return {"message": f"Emergency stop executed for strategy {strategy_id}"}
    else:
        return {"message": "Emergency stop executed for all strategies"}


@router.get("/metrics/{strategy_id}")
async def get_risk_metrics(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio risk metrics for a strategy."""
    risk_service = RiskManagementService(db)
    metrics = await risk_service.calculate_portfolio_risk_metrics(strategy_id)
    
    return metrics


