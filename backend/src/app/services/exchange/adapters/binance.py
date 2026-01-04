"""Binance exchange client implementation with low latency optimizations."""

import asyncio
import time
from typing import Any, Optional

import ccxt.async_support as ccxt
import structlog

from app.services.exchange.adapters.base import BaseExchangeClient

logger = structlog.get_logger(__name__)


class BinanceClient(BaseExchangeClient):
    """Binance exchange client with async support for low latency."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Binance client.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (always False for real trading)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.exchange: Optional[ccxt.binance] = None
        self._lock = asyncio.Lock()

    async def _get_exchange(self) -> ccxt.binance:
        """Get or create exchange instance (lazy initialization)."""
        if self.exchange is None:
            async with self._lock:
                if self.exchange is None:
                    config = {
                        "apiKey": self.api_key,
                        "secret": self.api_secret,
                        "enableRateLimit": True,
                        "options": {
                            "defaultType": "spot",
                        },
                    }
                    
                    if self.testnet:
                        config["urls"] = {
                            "api": {
                                "public": "https://testnet.binance.vision/api",
                                "private": "https://testnet.binance.vision/api",
                            }
                        }
                        config["options"]["sandbox"] = True
                        logger.info("Using Binance TESTNET (testnet.binance.vision)")
                    else:
                        logger.info("Using Binance PRODUCTION (real trading)")
                    
                    self.exchange = ccxt.binance(config)
        return self.exchange

    async def test_connection(self) -> bool:
        """Test exchange API connection with latency tracking."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            balance = await exchange.fetch_balance()
            latency_ms = (time.time() - start_time) * 1000
            logger.info("Connection test successful", latency_ms=latency_ms)
            return True
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Connection test failed", error=str(e), latency_ms=latency_ms)
            raise

    async def get_balance(self, currency: str = "USDT") -> float:
        """Get account balance for a currency with low latency."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            balance = await exchange.fetch_balance()
            free_balance = balance.get(currency, {}).get("free", 0.0)
            latency_ms = (time.time() - start_time) * 1000
            logger.info("Balance fetched", currency=currency, balance=free_balance, latency_ms=latency_ms)
            return float(free_balance)
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Failed to fetch balance", error=str(e), latency_ms=latency_ms)
            raise

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get current ticker price with low latency."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            ticker = await exchange.fetch_ticker(symbol)
            latency_ms = (time.time() - start_time) * 1000
            logger.debug("Ticker fetched", symbol=symbol, price=ticker["last"], latency_ms=latency_ms)
            return {
                "symbol": symbol,
                "price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "volume": ticker["quoteVolume"],
                "timestamp": ticker["timestamp"],
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Failed to fetch ticker", symbol=symbol, error=str(e), latency_ms=latency_ms)
            raise

    async def place_market_order(
        self, symbol: str, side: str, amount: float
    ) -> dict[str, Any]:
        """Place a market order with latency tracking."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            order = await exchange.create_market_order(symbol, side, amount)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Market order placed",
                symbol=symbol,
                side=side,
                amount=amount,
                order_id=order.get("id"),
                latency_ms=latency_ms,
            )
            return {
                "id": order.get("id"),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "status": order.get("status"),
                "filled": order.get("filled"),
                "price": order.get("price"),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to place market order",
                symbol=symbol,
                side=side,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def place_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> dict[str, Any]:
        """Place a limit order with latency tracking."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            order = await exchange.create_limit_order(symbol, side, amount, price)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Limit order placed",
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_id=order.get("id"),
                latency_ms=latency_ms,
            )
            return {
                "id": order.get("id"),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "status": order.get("status"),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to place limit order",
                symbol=symbol,
                side=side,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def place_stop_market_order(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> dict[str, Any]:
        """
        Place a stop-market order (for stop-loss).
        
        CRITICAL: This executes as MARKET order when stop_price is hit.
        Use this instead of LIMIT orders for stop-loss to ensure execution on gaps.
        """
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            order = await exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=side,
                amount=amount,
                params={
                    'stopPrice': stop_price,
                }
            )
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Stop-market order placed",
                symbol=symbol,
                side=side,
                amount=amount,
                stop_price=stop_price,
                order_id=order.get("id"),
                latency_ms=latency_ms,
            )
            return {
                "id": order.get("id"),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "stop_price": stop_price,
                "status": order.get("status"),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to place stop-market order",
                symbol=symbol,
                side=side,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def place_oco_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        limit_price: float,
    ) -> dict[str, Any]:
        """
        Place an OCO (One-Cancels-Other) order.
        
        OCO orders place two orders simultaneously:
        - Stop-loss order (STOP_MARKET)
        - Take-profit order (LIMIT)
        
        When one executes, the other is automatically cancelled.
        """
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            order = await exchange.create_order(
                symbol=symbol,
                type='OCO',
                side=side,
                amount=amount,
                price=limit_price,
                params={
                    'stopPrice': stop_price,
                    'stopLimitPrice': stop_price,
                }
            )
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "OCO order placed",
                symbol=symbol,
                side=side,
                amount=amount,
                stop_price=stop_price,
                limit_price=limit_price,
                order_id=order.get("orderListId"),
                latency_ms=latency_ms,
            )
            return {
                "id": order.get("orderListId"),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "stop_price": stop_price,
                "limit_price": limit_price,
                "status": order.get("status"),
                "orders": order.get("orders", []),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to place OCO order",
                symbol=symbol,
                side=side,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def get_order_status(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Get order status."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            order = await exchange.fetch_order(order_id, symbol)
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Order status fetched",
                order_id=order_id,
                symbol=symbol,
                status=order.get("status"),
                latency_ms=latency_ms,
            )
            return {
                "id": order.get("id"),
                "symbol": symbol,
                "status": order.get("status"),
                "filled": order.get("filled"),
                "remaining": order.get("remaining"),
                "price": order.get("price"),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to fetch order status",
                order_id=order_id,
                symbol=symbol,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            result = await exchange.cancel_order(order_id, symbol)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Order cancelled",
                order_id=order_id,
                symbol=symbol,
                latency_ms=latency_ms,
            )
            return True
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to cancel order",
                order_id=order_id,
                symbol=symbol,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[list]:
        """Get OHLCV (candlestick) data for technical indicators."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "OHLCV fetched",
                symbol=symbol,
                timeframe=timeframe,
                candles=len(ohlcv),
                latency_ms=latency_ms,
            )
            return ohlcv
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to fetch OHLCV",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        """Get order book depth data."""
        start_time = time.time()
        try:
            exchange = await self._get_exchange()
            orderbook = await exchange.fetch_order_book(symbol, limit=limit)
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Order book fetched",
                symbol=symbol,
                bids_count=len(orderbook.get("bids", [])),
                asks_count=len(orderbook.get("asks", [])),
                latency_ms=latency_ms,
            )
            return {
                "symbol": symbol,
                "bids": orderbook.get("bids", []),
                "asks": orderbook.get("asks", []),
                "timestamp": orderbook.get("timestamp"),
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to fetch order book",
                symbol=symbol,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

