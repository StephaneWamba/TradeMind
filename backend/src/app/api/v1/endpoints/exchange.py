"""Exchange management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.exchange import ExchangeConnection, Exchange
from app.services.exchange import ExchangeService

router = APIRouter()


@router.get("/connections")
async def list_connections(db: AsyncSession = Depends(get_db)):
    """List all exchange connections."""
    stmt = select(ExchangeConnection, Exchange).join(
        Exchange, ExchangeConnection.exchange_id == Exchange.id
    ).order_by(ExchangeConnection.id.desc())
    result = await db.execute(stmt)
    connections = result.all()

    return {
        "connections": [
            {
                "id": conn.id,
                "exchange": exchange.display_name,
                "exchange_name": exchange.name,
                "is_active": conn.is_active,
                "is_testnet": conn.is_testnet,
                "last_connected_at": conn.last_connected_at.isoformat() if conn.last_connected_at else None,
            }
            for conn, exchange in connections
        ]
    }


@router.post("/connect")
async def connect_exchange(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    testnet: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Connect to an exchange."""
    service = ExchangeService(db)
    try:
        result = await service.connect_exchange(exchange_name, api_key, api_secret, testnet=testnet)
        # Service returns dict with "id" key
        return {"status": "connected", "connection_id": result["id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_exchange_status(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get exchange connection status."""
    service = ExchangeService(db)
    status = await service.get_connection_status(connection_id)
    return status


@router.get("/balance")
async def get_balance(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get account balance."""
    service = ExchangeService(db)
    try:
        balance = await service.get_balance(connection_id)
        return balance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Check if it's an authentication error
        error_str = str(e).lower()
        if "invalid api" in error_str or "authentication" in error_str or "api-key" in error_str:
            raise HTTPException(
                status_code=401, detail=f"Invalid API credentials: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
