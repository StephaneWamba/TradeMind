"""Trade and order models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Order(Base):
    """Order model for tracking exchange orders."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(100))  # Exchange's order ID
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "BTC/USDT"
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # buy, sell
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)  # market, limit, stop_market, stop_loss, take_profit, oco
    # For OCO orders
    oco_group_id: Mapped[Optional[str]] = mapped_column(String(100))  # Links OCO orders together
    related_order_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to related order in OCO pair
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float)  # For limit orders
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, filled, cancelled, failed
    filled_amount: Mapped[Optional[float]] = mapped_column(Float)
    filled_price: Mapped[Optional[float]] = mapped_column(Float)
    fee: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Trade(Base):
    """Completed trade model."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_order_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to orders
    sell_order_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to orders (null if open)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[Optional[float]] = mapped_column(Float)  # Profit/Loss
    pnl_percent: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False
    )  # open, closed, stopped
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text)  # LLM's reasoning for the trade
    llm_confidence: Mapped[Optional[float]] = mapped_column(Float)  # LLM confidence 0-1
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


