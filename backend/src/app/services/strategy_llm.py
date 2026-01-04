"""LLM-powered strategy service with LangGraph workflow."""

import time
from typing import Any, Optional

import structlog

from app.domain.market.indicators import calculate_indicators
from app.services.llm.internet_service import InternetAccessService
from app.services.llm.grok_service import LLMService
from app.services.market import MarketDataService

logger = structlog.get_logger(__name__)


class LLMStrategyService:
    """Service for LLM-powered trading strategies with LangGraph workflow."""

    def __init__(
        self,
        llm_service: LLMService,
        market_service: MarketDataService,
        internet_service: InternetAccessService,
    ):
        """Initialize strategy service."""
        self.llm_service = llm_service
        self.market_service = market_service
        self.internet_service = internet_service

    async def analyze_and_decide(
        self,
        connection_id: int,
        symbol: str,
        strategy_id: int,
    ) -> dict[str, Any]:
        """
        Complete LangGraph workflow: collect data → analyze → decide.

        Args:
            connection_id: Exchange connection ID
            symbol: Trading pair (e.g., "BTC/USDT")
            strategy_id: Strategy ID

        Returns:
            Trading decision with full context
        """
        start_time = time.time()

        try:
            # Step 1: Collect Market Data (Exchange API)
            logger.info("Step 1: Collecting market data", symbol=symbol)
            ticker = await self.market_service.get_ticker(connection_id, symbol)

            # Step 2: News & Sentiment
            # Try to fetch news as fallback, but LLM will also use Agent Tools
            logger.info("Step 2: Fetching news/sentiment", symbol=symbol)
            try:
                # Fetch news as fallback context (LLM will also use web_search tool)
                news = await self.internet_service.fetch_crypto_news(symbol.split("/")[0])
                logger.info("News fetched as fallback",
                            symbol=symbol, count=len(news))
            except Exception as e:
                logger.warning(
                    "Failed to fetch news fallback, LLM will use Agent Tools", error=str(e))
                news = []

            # Sentiment will be fetched by LLM via x_search tool
            sentiment = None  # LLM fetches via x_search tool

            # Step 3: Calculate Technical Indicators (Multi-timeframe)
            logger.info("Step 3: Calculating technical indicators",
                        symbol=symbol)
            exchange_service = self.market_service.exchange_service
            client = await exchange_service.get_client(connection_id)

            # Fetch OHLCV data for multiple timeframes
            ohlcv_1h = await client.get_ohlcv(symbol, timeframe="1h", limit=100)
            ohlcv_4h = await client.get_ohlcv(symbol, timeframe="4h", limit=100)
            ohlcv_1d = await client.get_ohlcv(symbol, timeframe="1d", limit=100)

            # Extract prices and high/low for ATR
            prices_1h = [candle[4] for candle in ohlcv_1h]  # Close
            high_1h = [candle[2] for candle in ohlcv_1h]  # High
            low_1h = [candle[3] for candle in ohlcv_1h]  # Low

            prices_4h = [candle[4] for candle in ohlcv_4h]
            prices_1d = [candle[4] for candle in ohlcv_1d]

            # Calculate indicators for 1h (primary timeframe)
            indicators_1h = calculate_indicators(prices_1h, high_1h, low_1h)
            indicators_4h = calculate_indicators(prices_4h)
            indicators_1d = calculate_indicators(prices_1d)

            # Calculate ATR-based volatility
            atr = indicators_1h.get("atr")
            current_price = ticker.get("price", 0)
            volatility_percent = (atr / current_price *
                                  100) if atr and current_price > 0 else None

            # Step 4: LLM Analysis (Grok 4.1 Fast) with enhanced context
            logger.info("Step 4: LLM analysis", symbol=symbol)
            market_data = {
                "symbol": symbol,
                "price": current_price,
                "rsi_1h": indicators_1h.get("rsi"),
                "rsi_4h": indicators_4h.get("rsi"),
                "rsi_1d": indicators_1d.get("rsi"),
                "macd_1h": indicators_1h.get("macd"),
                "macd_4h": indicators_4h.get("macd"),
                "macd_1d": indicators_1d.get("macd"),
                "bollinger_bands_1h": indicators_1h.get("bollinger_bands"),
                "atr": atr,
                "volatility_percent": volatility_percent,
                "volume": ticker.get("volume", 0),
            }

            llm_result = await self.llm_service.analyze_market(
                market_data=market_data,
                news_context=news,
                sentiment=sentiment,
            )

            total_latency_ms = (time.time() - start_time) * 1000

            logger.info(
                "Strategy analysis complete",
                symbol=symbol,
                strategy_id=strategy_id,
                total_latency_ms=total_latency_ms,
            )

            return {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "market_data": market_data,
                "news_count": len(news),
                "llm_decision": llm_result.get("decision", ""),
                "llm_latency_ms": llm_result.get("latency_ms", 0),
                "total_latency_ms": total_latency_ms,
                "tokens_used": llm_result.get("tokens_used", 0),
            }

        except Exception as e:
            total_latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Strategy analysis failed",
                symbol=symbol,
                error=str(e),
                latency_ms=total_latency_ms,
            )
            raise
