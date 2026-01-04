"""Exchange and connection models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Exchange(Base):
    """Exchange information model."""

    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_base_url: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExchangeConnection(Base):
    """User's exchange API connection."""

    __tablename__ = "exchange_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(nullable=False)  # FK to exchanges
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted API key
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted secret
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Testnet mode flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    balance_usdt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Cached balance
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

