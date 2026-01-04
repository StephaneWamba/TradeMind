"""Backtest models for storing backtest results."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.strategy import Strategy


class Backtest(Base):
    """Backtest run results."""

    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exchange_connections.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)

    # Time period
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    timeframe: Mapped[str] = mapped_column(
        String(10), nullable=False)  # e.g., "1h", "4h", "1d"

    # Initial conditions
    initial_balance: Mapped[Decimal] = mapped_column(Float, nullable=False)
    initial_cash: Mapped[Decimal] = mapped_column(Float, nullable=False)

    # Results
    final_balance: Mapped[Decimal] = mapped_column(Float, nullable=False)
    final_cash: Mapped[Decimal] = mapped_column(Float, nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Float, nullable=False)
    total_pnl_percent: Mapped[Decimal] = mapped_column(Float, nullable=False)

    # Performance metrics
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_win: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_factor: Mapped[Optional[float]
                          ] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown_percent: Mapped[Optional[float]
                                 ] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional stats
    largest_win: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    largest_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_trade_duration_hours: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True)

    # Metadata
    status: Mapped[str] = mapped_column(
        String(20), default="completed")  # completed, failed, running
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    strategy: Mapped["Strategy"] = relationship(
        "Strategy", back_populates="backtests")
    trades: Mapped[list["BacktestTrade"]] = relationship(
        "BacktestTrade", back_populates="backtest", cascade="all, delete-orphan"
    )


class BacktestTrade(Base):
    """Individual trades from a backtest."""

    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtests.id"), nullable=False
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY, SELL
    entry_price: Mapped[Decimal] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Float, nullable=False)

    # Timestamps
    entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # P&L
    pnl: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    pnl_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Risk management
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[Decimal]
                        ] = mapped_column(Float, nullable=True)
    risk_reward_ratio: Mapped[Optional[float]
                              ] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="open"
    )  # open, closed, stopped_out, take_profit

    # Relationships
    backtest: Mapped["Backtest"] = relationship(
        "Backtest", back_populates="trades")
