"""Base exchange client interface for maintainability."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseExchangeClient(ABC):
    """Abstract base class for exchange clients ensuring consistent interface."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test exchange API connection."""
        pass

    @abstractmethod
    async def get_balance(self, currency: str = "USDT") -> float:
        """Get account balance for a currency."""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get current ticker price for a symbol."""
        pass

    @abstractmethod
    async def place_market_order(
        self, symbol: str, side: str, amount: float
    ) -> dict[str, Any]:
        """Place a market order."""
        pass

    @abstractmethod
    async def place_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> dict[str, Any]:
        """Place a limit order."""
        pass

    @abstractmethod
    async def place_stop_market_order(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> dict[str, Any]:
        """Place a stop-market order (for stop-loss)."""
        pass

    @abstractmethod
    async def place_oco_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        limit_price: float,
    ) -> dict[str, Any]:
        """Place an OCO (One-Cancels-Other) order."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Get order status."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[list]:
        """
        Get OHLCV (candlestick) data for technical indicators.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe (e.g., "1h", "4h", "1d")
            limit: Number of candles to fetch

        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        """
        Get order book depth data.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            limit: Number of price levels to fetch

        Returns:
            Dict with 'bids' and 'asks' lists
        """
        pass
