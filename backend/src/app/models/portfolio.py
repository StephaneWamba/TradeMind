"""Portfolio and position models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Portfolio(Base):
    """Portfolio snapshot for tracking overall performance."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    total_value_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    cash_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    invested_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_pnl_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    daily_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    daily_pnl_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Position(Base):
    """Current open position."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to trades
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Float)
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Float)
    unrealized_pnl_percent: Mapped[Optional[float]] = mapped_column(Float)
    # Trailing stop-loss fields
    trailing_stop_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trailing_stop_percent: Mapped[Optional[float]] = mapped_column(Float)  # Trailing distance (e.g., 2%)
    trailing_stop_trigger_price: Mapped[Optional[float]] = mapped_column(Float)  # Highest price reached (for trailing)
    stop_loss_order_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to orders (stop-loss order)
    take_profit_order_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to orders (take-profit order)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


