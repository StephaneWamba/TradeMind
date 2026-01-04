"""Strategy models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.backtest import Backtest


class Strategy(Base):
    """Trading strategy model."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "llm_agent"
    config: Mapped[dict] = mapped_column(JSON, nullable=False)  # Strategy configuration
    exchange_connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft, active, paused, stopped
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    backtests: Mapped[list["Backtest"]] = relationship("Backtest", back_populates="strategy")


class StrategyExecution(Base):
    """Strategy execution tracking for monitoring."""

    __tablename__ = "strategy_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_type: Mapped[str] = mapped_column(String(50), nullable=False)  # signal, decision, trade
    result: Mapped[Optional[dict]] = mapped_column(JSON)  # Execution result data
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text)  # LLM reasoning if applicable
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float)  # Latency tracking
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


