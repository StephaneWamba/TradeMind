"""Market data service for low latency price fetching."""

import asyncio
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_cache, set_cache
from app.services.exchange import ExchangeService

logger = structlog.get_logger(__name__)


class MarketDataService:
    """Service for market data operations optimized for low latency."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)

    async def get_ticker(self, connection_id: int, symbol: str) -> dict:
        """Get ticker for a single symbol with low latency."""
        # Check cache first (5 second TTL for price data)
        cache_key = f"ticker:{connection_id}:{symbol}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug("Ticker cache hit", connection_id=connection_id, symbol=symbol)
            return cached
        
        # Fetch from exchange
        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            ticker = await client.get_ticker(symbol)
            
            # Cache for 5 seconds (price data changes frequently)
            await set_cache(cache_key, ticker, ttl=5)
            
            return ticker
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning("Error closing exchange client", error=str(e))

    async def get_tickers(self, connection_id: int, symbols: list[str]) -> list[dict]:
        """Get multiple tickers efficiently with caching and parallel fetching."""
        exchange_service = ExchangeService(self.db)
        client = None
        try:
            client = await exchange_service.get_client(connection_id)
            
            # Check cache for all symbols
            cache_keys = [f"ticker:{connection_id}:{symbol}" for symbol in symbols]
            cached_tickers = await asyncio.gather(*[get_cache(key) for key in cache_keys])
            
            # Determine which symbols need fetching
            symbols_to_fetch = []
            tickers = []
            for i, (symbol, cached) in enumerate(zip(symbols, cached_tickers)):
                if cached:
                    tickers.append(cached)
                    logger.debug("Ticker cache hit", connection_id=connection_id, symbol=symbol)
                else:
                    symbols_to_fetch.append((i, symbol))
                    tickers.append(None)  # Placeholder
            
            # Fetch missing tickers in parallel
            if symbols_to_fetch:
                fetch_tasks = [client.get_ticker(symbol) for _, symbol in symbols_to_fetch]
                fetched_tickers = await asyncio.gather(*fetch_tasks)
                
                # Update results and cache
                for (i, symbol), ticker in zip(symbols_to_fetch, fetched_tickers):
                    tickers[i] = ticker
                    cache_key = f"ticker:{connection_id}:{symbol}"
                    await set_cache(cache_key, ticker, ttl=5)
            
            return tickers
        finally:
            # CRITICAL: Close exchange client to release aiohttp sessions
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning("Error closing exchange client", error=str(e))

