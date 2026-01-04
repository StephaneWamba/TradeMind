"""Strategy management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.models.strategy import Strategy
from app.models.exchange import ExchangeConnection
from app.schemas.strategy import StrategyCreate, StrategyResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("", response_model=dict)
async def list_strategies(db: AsyncSession = Depends(get_db)):
    """List all strategies."""
    stmt = select(Strategy).order_by(Strategy.created_at.desc())
    result = await db.execute(stmt)
    strategies = result.scalars().all()
    
    return {
        "strategies": [
            StrategyResponse.model_validate(strategy).model_dump()
            for strategy in strategies
        ]
    }


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new strategy."""
    # Validate exchange connection exists
    stmt = select(ExchangeConnection).where(
        ExchangeConnection.id == strategy_data.exchange_connection_id
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange connection {strategy_data.exchange_connection_id} not found",
        )
    
    if not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exchange connection {strategy_data.exchange_connection_id} is not active",
        )
    
    # Create strategy
    strategy = Strategy(
        name=strategy_data.name,
        description=strategy_data.description,
        strategy_type=strategy_data.strategy_type,
        config=strategy_data.config,
        exchange_connection_id=strategy_data.exchange_connection_id,
        status="draft",
        is_active=strategy_data.is_active,
    )
    
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    
    logger.info(
        "Strategy created",
        strategy_id=strategy.id,
        name=strategy.name,
        strategy_type=strategy.strategy_type,
    )
    
    # Use model_dump with mode='json' to properly serialize datetime objects
    return StrategyResponse.model_validate(strategy).model_dump(mode='json')

