"""WebSocket message schemas."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class WebSocketMessage(BaseModel):
    """Base WebSocket message."""

    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriceUpdateMessage(WebSocketMessage):
    """Price update message."""

    type: Literal["price_update"] = "price_update"
    connection_id: int
    symbol: str
    price: float
    change_24h: Optional[float] = None
    volume_24h: Optional[float] = None


class PositionUpdateMessage(WebSocketMessage):
    """Position update message."""

    type: Literal["position_update"] = "position_update"
    connection_id: int
    position_id: int
    symbol: str
    amount: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class PortfolioUpdateMessage(WebSocketMessage):
    """Portfolio value update message."""

    type: Literal["portfolio_update"] = "portfolio_update"
    connection_id: int
    total_value_usdt: float
    cash_usdt: float
    invested_usdt: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    daily_pnl: float
    daily_pnl_percent: float


class TradeEventMessage(WebSocketMessage):
    """Trade execution event message."""

    type: Literal["trade_event"] = "trade_event"
    connection_id: int
    trade_id: int
    strategy_id: int
    symbol: str
    side: str  # "buy" or "sell"
    amount: float
    price: float
    realized_pnl: Optional[float] = None


class PositionClosedMessage(WebSocketMessage):
    """Position closed message."""

    type: Literal["position_closed"] = "position_closed"
    connection_id: int
    position_id: int
    symbol: str
    final_pnl: float
    final_pnl_percent: float


class StrategyStatusMessage(WebSocketMessage):
    """Strategy status change message."""

    type: Literal["strategy_status"] = "strategy_status"
    connection_id: int
    strategy_id: int
    status: str  # "active", "paused", "stopped"
    performance: Optional[float] = None


class SubscriptionMessage(BaseModel):
    """Client subscription request."""

    action: Literal["subscribe", "unsubscribe"]
    channels: list[str]  # e.g., ["prices", "positions", "portfolio", "trades"]


class ErrorMessage(WebSocketMessage):
    """Error message."""

    type: Literal["error"] = "error"
    error: str
    code: Optional[str] = None


