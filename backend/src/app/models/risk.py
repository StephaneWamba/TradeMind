"""Risk management models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RiskConfig(Base):
    """Risk management configuration per strategy."""

    __tablename__ = "risk_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    max_position_size_percent: Mapped[float] = mapped_column(Float, default=0.02, nullable=False)  # 2% max
    max_daily_loss_percent: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)  # 5% max
    max_drawdown_percent: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)  # 10% max
    min_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 50% min
    position_sizing_method: Mapped[str] = mapped_column(String(20), default="fixed", nullable=False)  # fixed, kelly
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyLoss(Base):
    """Daily loss tracking per strategy."""

    __tablename__ = "daily_losses"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_loss: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_loss_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit_reached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CircuitBreaker(Base):
    """Circuit breaker state for strategies."""

    __tablename__ = "circuit_breakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trigger_reason: Mapped[Optional[str]] = mapped_column(String(255))
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


