"""Market data endpoints for low latency price fetching."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.market import MarketDataService
from app.services.exchange import ExchangeService
from app.domain.market.indicators import calculate_indicators

router = APIRouter()


@router.get("/ticker")
async def get_ticker(
    symbol: str,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get current ticker price for a symbol with low latency."""
    service = MarketDataService(db)
    try:
        ticker = await service.get_ticker(connection_id, symbol)
        return ticker
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Check if it's an authentication error
        error_str = str(e).lower()
        if "invalid api" in error_str or "authentication" in error_str or "api-key" in error_str:
            raise HTTPException(
                status_code=401, detail=f"Invalid API credentials: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tickers")
async def get_tickers(
    symbols: str,  # Comma-separated symbols
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get multiple tickers at once for efficiency."""
    service = MarketDataService(db)
    symbol_list = [s.strip() for s in symbols.split(",")]
    try:
        tickers = await service.get_tickers(connection_id, symbol_list)
        return {"tickers": tickers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/indicators")
async def get_indicators(
    symbol: str,
    connection_id: int,
    timeframe: str = "1h",
    db: AsyncSession = Depends(get_db),
):
    """
    Get technical indicators (RSI, MACD) calculated from actual OHLCV data.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        connection_id: Exchange connection ID
        timeframe: Timeframe for indicators (default: "1h")

    Returns:
        Dict with RSI, MACD, and trading signal
    """
    exchange_service = ExchangeService(db)
    client = None
    try:
        # Get exchange client
        client = await exchange_service.get_client(connection_id)

        # Fetch OHLCV data (need at least 100 candles for reliable indicators)
        ohlcv = await client.get_ohlcv(symbol, timeframe=timeframe, limit=100)

        if len(ohlcv) < 35:  # Need at least 35 for MACD (26+9)
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data: got {len(ohlcv)} candles, need at least 35"
            )

        # Extract price data
        prices = [candle[4] for candle in ohlcv]  # Close prices
        high = [candle[2] for candle in ohlcv]  # High prices
        low = [candle[3] for candle in ohlcv]  # Low prices

        # Calculate indicators
        indicators = calculate_indicators(prices, high, low)

        # Determine trading signal based on RSI and MACD
        rsi = indicators.get("rsi")
        macd = indicators.get("macd")

        signal = "NEUTRAL"
        if rsi is not None and macd is not None:
            histogram = macd.get("histogram", 0)
            if rsi < 30 and histogram > 0:
                signal = "BUY"
            elif rsi > 70 and histogram < 0:
                signal = "SELL"

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "atr": indicators.get("atr"),
            "bollinger_bands": indicators.get("bollinger_bands"),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_str = str(e).lower()
        if "invalid api" in error_str or "authentication" in error_str or "api-key" in error_str:
            raise HTTPException(
                status_code=401, detail=f"Invalid API credentials: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Close exchange client
        if client:
            try:
                await client.close()
            except Exception:
                pass
