"""Technical indicators calculation using pandas-ta."""

import pandas as pd
import pandas_ta as ta
import structlog

logger = structlog.get_logger(__name__)


def calculate_atr(high: list[float], low: list[float], close: list[float], period: int = 14) -> float | None:
    """
    Calculate ATR (Average True Range) for volatility-based position sizing.
    
    Args:
        high: List of high prices
        low: List of low prices
        close: List of closing prices
        period: ATR period (default 14)
    
    Returns:
        ATR value or None if insufficient data
    """
    if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
        logger.warning("Insufficient data for ATR", data_points=len(close), required=period + 1)
        return None
    
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    atr = ta.atr(df["high"], df["low"], df["close"], length=period)
    
    if atr is None or atr.empty:
        return None
    
    return float(atr.iloc[-1])


def calculate_bollinger_bands(prices: list[float], period: int = 20, std_dev: float = 2.0) -> dict[str, float] | None:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of closing prices
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
    
    Returns:
        Dict with 'upper', 'middle', 'lower' bands or None
    """
    if len(prices) < period:
        logger.warning("Insufficient data for Bollinger Bands", data_points=len(prices), required=period)
        return None
    
    df = pd.DataFrame({"close": prices})
    bb = ta.bbands(df["close"], length=period, std=std_dev)
    
    if bb is None or bb.empty:
        return None
    
    last_row = bb.iloc[-1]
    upper_key = f"BBU_{period}_{std_dev}"
    middle_key = f"BBM_{period}_{std_dev}"
    lower_key = f"BBL_{period}_{std_dev}"
    
    if upper_key not in last_row.index:
        upper_key = f"BBU_{period}_{int(std_dev)}"
        middle_key = f"BBM_{period}_{int(std_dev)}"
        lower_key = f"BBL_{period}_{int(std_dev)}"
    
    if upper_key not in last_row.index:
        bb_columns = [col for col in bb.columns if col.startswith("BB")]
        if len(bb_columns) >= 3:
            upper_key = bb_columns[0]
            middle_key = bb_columns[1]
            lower_key = bb_columns[2]
        else:
            logger.warning("Could not find Bollinger Bands columns", available_columns=list(bb.columns))
            return None
    
    return {
        "upper": float(last_row[upper_key]),
        "middle": float(last_row[middle_key]),
        "lower": float(last_row[lower_key]),
    }


def calculate_rsi(prices: list[float], period: int = 14) -> float | None:
    """
    Calculate RSI (Relative Strength Index).
    
    Args:
        prices: List of closing prices (most recent last)
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        logger.warning("Insufficient data for RSI", data_points=len(prices), required=period + 1)
        return None
    
    df = pd.DataFrame({"close": prices})
    rsi = ta.rsi(df["close"], length=period)
    
    if rsi is None or rsi.empty:
        return None
    
    return float(rsi.iloc[-1])


def calculate_macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, float] | None:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: List of closing prices (most recent last)
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
    
    Returns:
        Dict with 'macd', 'signal', 'histogram' or None if insufficient data
    """
    if len(prices) < slow + signal:
        logger.warning(
            "Insufficient data for MACD",
            data_points=len(prices),
            required=slow + signal,
        )
        return None
    
    df = pd.DataFrame({"close": prices})
    macd_data = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    
    if macd_data is None or macd_data.empty:
        return None
    
    last_row = macd_data.iloc[-1]
    return {
        "macd": float(last_row[f"MACD_{fast}_{slow}_{signal}"]),
        "signal": float(last_row[f"MACDs_{fast}_{slow}_{signal}"]),
        "histogram": float(last_row[f"MACDh_{fast}_{slow}_{signal}"]),
    }


def calculate_indicators(
    prices: list[float],
    high: list[float] | None = None,
    low: list[float] | None = None,
) -> dict[str, float | dict | None]:
    """
    Calculate all technical indicators.
    
    Args:
        prices: List of closing prices (most recent last)
        high: List of high prices (optional, for ATR)
        low: List of low prices (optional, for ATR)
    
    Returns:
        Dict with 'rsi', 'macd', 'atr', 'bollinger_bands' indicators
    """
    indicators = {
        "rsi": calculate_rsi(prices),
        "macd": calculate_macd(prices),
        "bollinger_bands": calculate_bollinger_bands(prices),
    }
    
    if high and low and len(high) == len(low) == len(prices):
        indicators["atr"] = calculate_atr(high, low, prices)
    
    return indicators

