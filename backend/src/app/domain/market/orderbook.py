"""Order book depth analysis domain logic."""

import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exchange import ExchangeService

logger = structlog.get_logger(__name__)


class OrderBookService:
    """Service for analyzing order book depth."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)

    async def analyze_order_book(self, connection_id: int, symbol: str, depth: int = 20) -> dict[str, Any]:
        """
        Analyze order book depth for entry/exit timing.

        Returns:
            Dict with order book metrics:
            - bid_volume: Total volume on bid side
            - ask_volume: Total volume on ask side
            - imbalance: (bid_volume - ask_volume) / (bid_volume + ask_volume)
            - support_level: Strongest bid level
            - resistance_level: Strongest ask level
            - spread: Current spread
        """
        try:
            client = await self.exchange_service.get_client(connection_id)
            orderbook = await client.get_order_book(symbol, limit=depth)

            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return {
                    "symbol": symbol,
                    "error": "Insufficient order book data",
                }

            bid_volume = sum(price * amount for price, amount in bids)
            ask_volume = sum(price * amount for price, amount in asks)
            total_volume = bid_volume + ask_volume

            imbalance = (bid_volume - ask_volume) / \
                total_volume if total_volume > 0 else 0.0

            support_level = None
            support_volume = 0
            for price, amount in bids[:5]:
                volume = price * amount
                if volume > support_volume:
                    support_volume = volume
                    support_level = price

            resistance_level = None
            resistance_volume = 0
            for price, amount in asks[:5]:
                volume = price * amount
                if volume > resistance_volume:
                    resistance_volume = volume
                    resistance_level = price

            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            spread = best_ask - best_bid
            spread_percent = (spread / best_bid * 100) if best_bid > 0 else 0

            return {
                "symbol": symbol,
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "imbalance": imbalance,
                "support_level": support_level,
                "resistance_level": resistance_level,
                "spread": spread,
                "spread_percent": spread_percent,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "interpretation": self._interpret_imbalance(imbalance),
            }
        except Exception as e:
            logger.error("Failed to analyze order book",
                         symbol=symbol, error=str(e))
            raise

    def _interpret_imbalance(self, imbalance: float) -> str:
        """Interpret order book imbalance."""
        if imbalance > 0.3:
            return "Strong buy pressure - bullish"
        elif imbalance > 0.1:
            return "Moderate buy pressure"
        elif imbalance > -0.1:
            return "Balanced"
        elif imbalance > -0.3:
            return "Moderate sell pressure"
        else:
            return "Strong sell pressure - bearish"
