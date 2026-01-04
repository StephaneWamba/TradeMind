"""Order placement endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.orders import OrderService
from app.models.trade import Trade, Order
from app.models.strategy import Strategy

router = APIRouter()


class MarketOrderRequest(BaseModel):
    """Market order request model."""

    connection_id: int
    symbol: str
    side: str  # buy or sell
    amount: float


class LimitOrderRequest(BaseModel):
    """Limit order request model."""

    connection_id: int
    symbol: str
    side: str  # buy or sell
    amount: float
    price: float


@router.post("/market")
async def place_market_order(
    request: MarketOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Place a market order with low latency."""
    service = OrderService(db)
    try:
        order = await service.place_market_order(
            request.connection_id,
            request.symbol,
            request.side,
            request.amount,
        )
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/limit")
async def place_limit_order(
    request: LimitOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Place a limit order."""
    service = OrderService(db)
    try:
        order = await service.place_limit_order(
            request.connection_id,
            request.symbol,
            request.side,
            request.amount,
            request.price,
        )
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}")
async def get_order_status(
    order_id: str,
    symbol: str,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get order status."""
    service = OrderService(db)
    try:
        status = await service.get_order_status(connection_id, order_id, symbol)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str,
    symbol: str,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order."""
    service = OrderService(db)
    try:
        result = await service.cancel_order(connection_id, order_id, symbol)
        return {"success": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/trades/list")
async def get_trades(
    connection_id: Optional[int] = Query(
        None, description="Exchange connection ID"),
    strategy_id: Optional[int] = Query(None, description="Strategy ID filter"),
    limit: int = Query(50, description="Number of trades to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get list of trades (historical)."""
    try:
        # Build query
        stmt = select(Trade).order_by(desc(Trade.created_at))

        # Filter by strategy_id if provided
        if strategy_id:
            stmt = stmt.where(Trade.strategy_id == strategy_id)
        # Filter by connection_id if provided (via strategies)
        elif connection_id:
            # Join with Strategy to filter by connection_id
            stmt = select(Trade).join(
                Strategy, Trade.strategy_id == Strategy.id
            ).where(
                Strategy.exchange_connection_id == connection_id
            ).order_by(desc(Trade.created_at))

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        trades = result.scalars().all()

        # Format response
        trades_list = []
        for trade in trades:
            # Get buy order for price/amount
            buy_order = None
            if trade.buy_order_id:
                buy_stmt = select(Order).where(Order.id == trade.buy_order_id)
                buy_result = await db.execute(buy_stmt)
                buy_order = buy_result.scalar_one_or_none()

            trades_list.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "side": "buy" if trade.status == "open" else "sell",
                "amount": trade.amount,
                "price": buy_order.filled_price if buy_order and buy_order.filled_price else trade.entry_price,
                "realized_pnl": trade.pnl,
                "realized_pnl_percent": trade.pnl_percent,
                "status": trade.status,
                "timestamp": trade.entry_time.isoformat() if trade.entry_time else trade.created_at.isoformat(),
            })

        return {"trades": trades_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
