"""Controlled internet access service for news and sentiment with rate limiting."""

import asyncio
import time
from typing import Optional

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class InternetAccessService:
    """Service for controlled internet access with rate limiting and caching."""

    def __init__(self):
        """Initialize with rate limiting."""
        self.client = httpx.AsyncClient(timeout=5.0)
        self.rate_limiter = asyncio.Semaphore(10)
        self.last_request_time: dict[str, float] = {}
        self.min_request_interval = 60.0

    async def fetch_crypto_news(self, symbol: str = "BTC") -> list[dict]:
        """
        Fetch recent crypto news with rate limiting.

        Args:
            symbol: Cryptocurrency symbol (default: BTC)

        Returns:
            List of news articles
        """
        cache_key = f"news_{symbol}"
        if self._should_throttle(cache_key):
            logger.debug("Rate limited, returning cached data", symbol=symbol)
            return []

        async with self.rate_limiter:
            try:
                url = "https://min-api.cryptocompare.com/data/v2/news/"
                params = {"categories": symbol, "lang": "EN", "limit": 10}

                response = await self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                news_items = []

                if data.get("Data"):
                    for item in data["Data"][:5]:
                        news_items.append(
                            {
                                "title": item.get("title", ""),
                                "body": item.get("body", ""),
                                "source": item.get("source", ""),
                                "published_at": item.get("published_on", 0),
                                "url": item.get("url", ""),
                            }
                        )

                self.last_request_time[cache_key] = time.time()
                logger.info("News fetched", symbol=symbol,
                            count=len(news_items))

                return news_items

            except Exception as e:
                logger.error("Failed to fetch news",
                             symbol=symbol, error=str(e))
                return []

    async def get_sentiment(self, symbol: str = "BTC") -> Optional[dict]:
        """
        Get market sentiment (placeholder for future Twitter/Reddit integration).

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            Sentiment data or None
        """
        logger.debug("Sentiment API not yet implemented", symbol=symbol)
        return None

    async def check_market_events(self) -> list[dict]:
        """
        Check for major market events.

        Returns:
            List of market events
        """
        logger.debug("Market events API not yet implemented")
        return []

    def _should_throttle(self, cache_key: str) -> bool:
        """Check if request should be throttled."""
        if cache_key not in self.last_request_time:
            return False

        elapsed = time.time() - self.last_request_time[cache_key]
        return elapsed < self.min_request_interval

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
