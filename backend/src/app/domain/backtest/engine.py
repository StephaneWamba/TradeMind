"""Backtesting engine for testing strategies on historical data."""

import math
import statistics
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import structlog

from app.services.exchange import ExchangeService
from app.domain.market.indicators import calculate_indicators
from app.services.llm.grok_service import LLMService
from app.services.market import MarketDataService
from app.services.strategy_llm import LLMStrategyService
from app.services.llm.internet_service import InternetAccessService
from app.services.llm.tavily_service import TavilyService
from app.schemas.llm import TradingDecision

logger = structlog.get_logger(__name__)


class BacktestService:
    """Service for running backtests on historical data."""

    def __init__(self, db):
        """Initialize backtest service."""
        self.db = db
        self.exchange_service = ExchangeService(db) if db else None
        self._cached_decision = None

    async def run_backtest(
        self,
        strategy_id: int,
        connection_id: int,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1h",
        initial_balance: float = 10000.0,
        pre_fetched_client: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Run a backtest on historical data.

        Args:
            strategy_id: Strategy ID to test
            connection_id: Exchange connection ID
            symbol: Trading pair (e.g., "BTC/USDT")
            start_date: Start date for backtest
            end_date: End date for backtest
            timeframe: Timeframe for candles (e.g., "1h", "4h", "1d")
            initial_balance: Starting balance in USDT

        Returns:
            Backtest results with performance metrics
        """
        logger.info(
            "Starting backtest",
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            timeframe=timeframe,
        )

        try:
            if pre_fetched_client:
                client = pre_fetched_client
            else:
                client = await self.exchange_service.get_client(connection_id)

            tavily_service = TavilyService()
            llm_service = LLMService(tavily_service=tavily_service)
            internet_service = InternetAccessService()

            timeframe_minutes = self._timeframe_to_minutes(timeframe)
            total_minutes = int((end_date - start_date).total_seconds() / 60)
            num_candles = math.ceil(total_minutes / timeframe_minutes) + 100

            logger.info("Fetching historical data", num_candles=num_candles)
            ohlcv_data = await client.get_ohlcv(
                symbol, timeframe=timeframe, limit=num_candles
            )

            if len(ohlcv_data) < 100:
                raise ValueError(
                    f"Insufficient historical data: got {len(ohlcv_data)} candles, need at least 100"
                )

            filtered_ohlcv = []
            for candle in ohlcv_data:
                candle_time = datetime.fromtimestamp(
                    candle[0] / 1000, tz=timezone.utc)
                if start_date <= candle_time <= end_date:
                    filtered_ohlcv.append(candle)

            if not filtered_ohlcv:
                raise ValueError("No data in specified date range")

            logger.info(
                "Historical data filtered",
                total_candles=len(filtered_ohlcv),
                date_range=f"{filtered_ohlcv[0][0]} to {filtered_ohlcv[-1][0]}",
            )

            cash = Decimal(str(initial_balance))
            positions: dict[str, dict] = {}
            trades: list[dict] = []
            equity_curve: list[dict] = []

            for i, candle in enumerate(filtered_ohlcv):
                candle_time = datetime.fromtimestamp(
                    candle[0] / 1000, tz=timezone.utc)
                open_price = Decimal(str(candle[1]))
                high_price = Decimal(str(candle[2]))
                low_price = Decimal(str(candle[3]))
                close_price = Decimal(str(candle[4]))
                volume = Decimal(str(candle[5]))

                if i >= 100:
                    historical_candles = filtered_ohlcv[: i + 1]
                    prices = [c[4] for c in historical_candles]
                    highs = [c[2] for c in historical_candles]
                    lows = [c[3] for c in historical_candles]

                    indicators = calculate_indicators(prices, highs, lows)

                    market_data = {
                        "symbol": symbol,
                        "price": float(close_price),
                        "volume": float(volume),
                        "rsi_1h": indicators.get("rsi"),
                        "macd_1h": indicators.get("macd"),
                        "atr": indicators.get("atr", 0),
                        "volatility_percent": (
                            indicators.get("atr", 0) / float(close_price) * 100
                            if close_price > 0
                            else 0
                        ),
                    }

                    decision = None
                    llm_call_interval = 6
                    should_call_llm = (i % llm_call_interval == 0) or (
                        i == len(filtered_ohlcv) - 1)

                    if should_call_llm:
                        try:
                            ohlcv_4h = await client.get_ohlcv(symbol, timeframe="4h", limit=100) if i >= 400 else None
                            ohlcv_1d = await client.get_ohlcv(symbol, timeframe="1d", limit=100) if i >= 2400 else None

                            if ohlcv_4h and len(ohlcv_4h) >= 35:
                                prices_4h = [c[4] for c in ohlcv_4h]
                                highs_4h = [c[2] for c in ohlcv_4h]
                                lows_4h = [c[3] for c in ohlcv_4h]
                                indicators_4h = calculate_indicators(
                                    prices_4h, highs_4h, lows_4h)
                                market_data["rsi_4h"] = indicators_4h.get(
                                    "rsi")
                                market_data["macd_4h"] = indicators_4h.get(
                                    "macd")

                            if ohlcv_1d and len(ohlcv_1d) >= 35:
                                prices_1d = [c[4] for c in ohlcv_1d]
                                highs_1d = [c[2] for c in ohlcv_1d]
                                lows_1d = [c[3] for c in ohlcv_1d]
                                indicators_1d = calculate_indicators(
                                    prices_1d, highs_1d, lows_1d)
                                market_data["rsi_1d"] = indicators_1d.get(
                                    "rsi")
                                market_data["macd_1d"] = indicators_1d.get(
                                    "macd")

                            trading_decision = await llm_service.analyze_market_structured(
                                market_data=market_data,
                                response_model=TradingDecision,
                            )

                            decision = self._convert_structured_decision(
                                trading_decision, market_data)

                            self._cached_decision = decision

                            logger.debug(
                                "LLM structured decision received",
                                action=decision["action"],
                                confidence=decision["confidence"],
                                symbol=symbol,
                            )

                        except Exception as e:
                            logger.warning(
                                "Structured LLM call failed, using simplified decision",
                                error=str(e),
                                symbol=symbol,
                            )
                            decision = self._get_simplified_decision(
                                market_data, indicators)
                            self._cached_decision = decision
                    else:
                        if hasattr(self, '_cached_decision') and self._cached_decision:
                            decision = self._cached_decision
                        else:
                            decision = self._get_simplified_decision(
                                market_data, indicators)

                    min_confidence = 0.6
                    if (
                        decision["action"] == "BUY"
                        and symbol not in positions
                        and decision.get("confidence", 0) >= min_confidence
                    ):
                        position_size = self._calculate_position_size(
                            cash, market_data, decision)
                        if position_size > 0:
                            cost = position_size * close_price
                            if cost <= cash:
                                positions[symbol] = {
                                    "entry_price": close_price,
                                    "quantity": position_size,
                                    "entry_time": candle_time,
                                    "stop_loss": decision.get("stop_loss"),
                                    "take_profit": decision.get("take_profit"),
                                    "confidence": decision.get("confidence"),
                                    "reasoning": decision.get("reasoning", ""),
                                    "risk_factors": decision.get("risk_factors", []),
                                }
                                cash -= cost
                                logger.debug(
                                    "Position opened",
                                    symbol=symbol,
                                    price=float(close_price),
                                    quantity=float(position_size),
                                    confidence=decision.get("confidence"),
                                )

                    elif decision["action"] == "SELL" and symbol in positions:
                        position = positions.pop(symbol)
                        revenue = position["quantity"] * close_price
                        pnl = revenue - \
                            (position["quantity"] * position["entry_price"])
                        pnl_percent = (
                            (close_price - position["entry_price"])
                            / position["entry_price"]
                            * 100
                        )

                        cash += revenue

                        trades.append(
                            {
                                "symbol": symbol,
                                "side": "BUY",
                                "entry_price": float(position["entry_price"]),
                                "exit_price": float(close_price),
                                "quantity": float(position["quantity"]),
                                "entry_time": position["entry_time"],
                                "exit_time": candle_time,
                                "pnl": float(pnl),
                                "pnl_percent": float(pnl_percent),
                                "status": "closed",
                            }
                        )

                        logger.debug(
                            "Position closed",
                            symbol=symbol,
                            pnl=float(pnl),
                            pnl_percent=float(pnl_percent),
                        )

                    for pos_symbol, position in list(positions.items()):
                        if position.get("stop_loss") and low_price <= Decimal(
                            str(position["stop_loss"])
                        ):
                            revenue = position["quantity"] * Decimal(
                                str(position["stop_loss"])
                            )
                            pnl = revenue - (
                                position["quantity"] * position["entry_price"]
                            )
                            pnl_percent = (
                                (Decimal(
                                    str(position["stop_loss"])) - position["entry_price"])
                                / position["entry_price"]
                                * 100
                            )
                            cash += revenue
                            trades.append(
                                {
                                    "symbol": pos_symbol,
                                    "side": "BUY",
                                    "entry_price": float(position["entry_price"]),
                                    "exit_price": float(position["stop_loss"]),
                                    "quantity": float(position["quantity"]),
                                    "entry_time": position["entry_time"],
                                    "exit_time": candle_time,
                                    "pnl": float(pnl),
                                    "pnl_percent": float(pnl_percent),
                                    "status": "stopped_out",
                                }
                            )
                            del positions[pos_symbol]

                        elif position.get("take_profit") and high_price >= Decimal(
                            str(position["take_profit"])
                        ):
                            revenue = position["quantity"] * Decimal(
                                str(position["take_profit"])
                            )
                            pnl = revenue - (
                                position["quantity"] * position["entry_price"]
                            )
                            pnl_percent = (
                                (Decimal(
                                    str(position["take_profit"])) - position["entry_price"])
                                / position["entry_price"]
                                * 100
                            )
                            cash += revenue
                            trades.append(
                                {
                                    "symbol": pos_symbol,
                                    "side": "BUY",
                                    "entry_price": float(position["entry_price"]),
                                    "exit_price": float(position["take_profit"]),
                                    "quantity": float(position["quantity"]),
                                    "entry_time": position["entry_time"],
                                    "exit_time": candle_time,
                                    "pnl": float(pnl),
                                    "pnl_percent": float(pnl_percent),
                                    "status": "take_profit",
                                }
                            )
                            del positions[pos_symbol]

                current_equity = cash
                for pos_symbol, position in positions.items():
                    current_equity += position["quantity"] * close_price

                equity_curve.append(
                    {
                        "timestamp": candle_time.isoformat(),
                        "equity": float(current_equity),
                        "cash": float(cash),
                    }
                )

            final_price = Decimal(str(filtered_ohlcv[-1][4]))
            for pos_symbol, position in list(positions.items()):
                revenue = position["quantity"] * final_price
                pnl = revenue - (position["quantity"]
                                 * position["entry_price"])
                pnl_percent = (
                    (final_price - position["entry_price"]
                     ) / position["entry_price"] * 100
                )
                cash += revenue
                trades.append(
                    {
                        "symbol": pos_symbol,
                        "side": "BUY",
                        "entry_price": float(position["entry_price"]),
                        "exit_price": float(final_price),
                        "quantity": float(position["quantity"]),
                        "entry_time": position["entry_time"],
                        "exit_time": datetime.fromtimestamp(
                            filtered_ohlcv[-1][0] / 1000, tz=timezone.utc
                        ),
                        "pnl": float(pnl),
                        "pnl_percent": float(pnl_percent),
                        "status": "closed",
                    }
                )

            final_balance = float(cash)
            total_pnl = final_balance - initial_balance
            total_pnl_percent = (
                total_pnl / initial_balance * 100) if initial_balance > 0 else 0

            metrics = self._calculate_metrics(
                trades, initial_balance, equity_curve, total_pnl_percent
            )

            result = {
                "strategy_id": strategy_id,
                "connection_id": connection_id,
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timeframe": timeframe,
                "initial_balance": initial_balance,
                "initial_cash": initial_balance,
                "final_balance": final_balance,
                "final_cash": final_balance,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "total_trades": len(trades),
                "trades": trades,
                "equity_curve": equity_curve,
                **metrics,
            }

            logger.info(
                "Backtest completed",
                strategy_id=strategy_id,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                total_trades=len(trades),
            )

            return result

        except Exception as e:
            logger.error("Backtest failed", error=str(e),
                         strategy_id=strategy_id)
            raise

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        timeframe_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080,
        }
        return timeframe_map.get(timeframe, 60)

    def _convert_structured_decision(
        self, trading_decision: TradingDecision, market_data: dict
    ) -> dict[str, Any]:
        """Convert structured TradingDecision to dict format for backtest execution."""
        price = market_data["price"]
        atr = market_data.get("atr", price * 0.02)

        stop_loss = None
        take_profit = None

        if trading_decision.action == "BUY":
            if trading_decision.stop_loss_percent is not None:
                stop_loss = price * (1 - trading_decision.stop_loss_percent)
            else:
                stop_loss = price - (atr * 2)

            if trading_decision.take_profit_percent is not None:
                take_profit = price * \
                    (1 + trading_decision.take_profit_percent)
            else:
                take_profit = price + (atr * 4)

        return {
            "action": trading_decision.action,
            "confidence": trading_decision.confidence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size_percent": trading_decision.position_size_percent,
            "reasoning": trading_decision.reasoning,
            "risk_factors": trading_decision.risk_factors,
        }

    def _get_simplified_decision(
        self, market_data: dict, indicators: dict
    ) -> dict[str, Any]:
        """Get simplified trading decision based on indicators (for backtesting)."""
        rsi = indicators.get("rsi")
        macd = indicators.get("macd", {})
        histogram = macd.get("histogram", 0) if isinstance(macd, dict) else 0

        action = "HOLD"
        confidence = 0.5

        if rsi is not None:
            if rsi < 30 and histogram > 0:
                action = "BUY"
                confidence = 0.7
            elif rsi > 70 and histogram < 0:
                action = "SELL"
                confidence = 0.7

        price = market_data["price"]
        atr = market_data.get("atr", price * 0.02)

        stop_loss = None
        take_profit = None

        if action == "BUY":
            stop_loss = price - (atr * 2)
            take_profit = price + (atr * 4)

        return {
            "action": action,
            "confidence": confidence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }

    def _calculate_position_size(
        self, cash: Decimal, market_data: dict, decision: dict
    ) -> Decimal:
        """Calculate position size based on risk management."""
        price = Decimal(str(market_data["price"]))
        atr = Decimal(str(market_data.get("atr", price * Decimal("0.02"))))
        volatility = market_data.get("volatility_percent", 2.0)

        if "position_size_percent" in decision and decision["position_size_percent"] > 0:
            risk_percent = Decimal(str(decision["position_size_percent"]))
        else:
            risk_percent = Decimal("0.01")
            if volatility > 5:
                risk_percent = Decimal("0.005")
            elif volatility < 1:
                risk_percent = Decimal("0.015")

        position_value = cash * risk_percent
        quantity = position_value / price

        return quantity

    def _calculate_metrics(
        self,
        trades: list[dict],
        initial_balance: float,
        equity_curve: list[dict],
        total_pnl_percent: float,
    ) -> dict[str, Any]:
        """Calculate performance metrics."""
        if not trades:
            return {
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_percent": 0.0,
                "sharpe_ratio": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_trade_duration_hours": 0.0,
            }

        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) <= 0]

        win_rate = (
            len(winning_trades) / len(trades) * 100 if trades else 0.0
        )

        avg_win = (
            statistics.mean([t["pnl"] for t in winning_trades])
            if winning_trades
            else 0.0
        )
        avg_loss = (
            statistics.mean([abs(t["pnl"]) for t in losing_trades])
            if losing_trades
            else 0.0
        )

        total_wins = sum(t["pnl"] for t in winning_trades)
        total_losses = abs(sum(t["pnl"] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        equity_values = [e["equity"] for e in equity_curve]
        peak = initial_balance
        max_drawdown = 0.0
        max_drawdown_percent = 0.0

        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            drawdown_percent = (drawdown / peak * 100) if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent

        if len(equity_curve) > 1:
            returns = [
                (equity_curve[i]["equity"] - equity_curve[i - 1]["equity"])
                / equity_curve[i - 1]["equity"]
                for i in range(1, len(equity_curve))
            ]
            if returns:
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(
                    returns) if len(returns) > 1 else 0.0
                sharpe_ratio = (
                    (avg_return / std_return * math.sqrt(252))
                    if std_return > 0
                    else 0.0
                )
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        largest_win = max([t["pnl"] for t in trades], default=0.0)
        largest_loss = min([t["pnl"] for t in trades], default=0.0)

        durations = []
        for trade in trades:
            if trade.get("entry_time") and trade.get("exit_time"):
                entry = datetime.fromisoformat(
                    trade["entry_time"].isoformat()
                    if isinstance(trade["entry_time"], datetime)
                    else trade["entry_time"]
                )
                exit_time = datetime.fromisoformat(
                    trade["exit_time"].isoformat()
                    if isinstance(trade["exit_time"], datetime)
                    else trade["exit_time"]
                )
                duration = (exit_time - entry).total_seconds() / 3600
                durations.append(duration)

        avg_trade_duration = (
            statistics.mean(durations) if durations else 0.0
        )

        return {
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "max_drawdown_percent": max_drawdown_percent,
            "sharpe_ratio": sharpe_ratio,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_trade_duration_hours": avg_trade_duration,
        }
