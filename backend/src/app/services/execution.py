"""Order execution service that integrates LLM decisions with order placement."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Order, Trade
from app.models.portfolio import Position
from app.schemas.llm import TradingDecision
from app.services.exchange import ExchangeService
from app.services.orders import OrderService
from app.domain.risk.management import RiskManagementService
from app.services.notification.alerting import AlertingService
from app.core.events import event_bus

logger = structlog.get_logger(__name__)


class ExecutionService:
    """Service for executing LLM trading decisions with validation and tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exchange_service = ExchangeService(db)
        self.order_service = OrderService(db)
        self.risk_service = RiskManagementService(db)
        self.alerting_service = AlertingService()

    async def execute_llm_decision(
        self,
        connection_id: int,
        strategy_id: int,
        symbol: str,
        decision: TradingDecision,
        current_price: float,
        atr: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Execute an LLM trading decision with validation and tracking.
        
        Args:
            connection_id: Exchange connection ID
            strategy_id: Strategy ID
            symbol: Trading pair (e.g., "BTC/USDT")
            decision: LLM trading decision (structured)
            current_price: Current market price
            atr: Average True Range for volatility-based position sizing (optional)
        
        Returns:
            Execution result with order details and trade info
        """
        start_time = time.time()
        
        try:
            # Step 0: Check circuit breaker
            circuit_breaker_active = await self.risk_service.check_circuit_breaker(strategy_id)
            if circuit_breaker_active:
                # Alert already sent when circuit breaker was triggered
                return {
                    "executed": False,
                    "reason": "Circuit breaker is active - trading paused",
                    "decision": decision.model_dump(),
                }
            
            # Step 0.5: Check daily loss limit
            daily_loss_check = await self.risk_service.check_daily_loss_limit(strategy_id)
            if daily_loss_check["limit_reached"]:
                # Alert already sent when limit was reached
                return {
                    "executed": False,
                    "reason": f"Daily loss limit reached: {daily_loss_check['current_loss']:.2f}%",
                    "decision": decision.model_dump(),
                }
            
            # Step 1: Validate decision
            logger.info(
                "Validating LLM decision",
                strategy_id=strategy_id,
                symbol=symbol,
                action=decision.action,
                confidence=decision.confidence,
            )
            
            validation_result = await self._validate_decision(
                connection_id, strategy_id, symbol, decision, current_price
            )
            
            if not validation_result["valid"]:
                logger.warning(
                    "Decision validation failed",
                    strategy_id=strategy_id,
                    reason=validation_result["reason"],
                )
                return {
                    "executed": False,
                    "reason": validation_result["reason"],
                    "decision": decision.model_dump(),
                }
            
            # Step 2: Calculate position size using risk management
            balance = await self.exchange_service.get_balance(connection_id)
            available_usdt = balance.get("usdt", 0.0)
            
            if decision.action == "BUY":
                # Get risk config for position sizing method
                risk_config = await self.risk_service.get_risk_config(strategy_id)
                
                # Get portfolio metrics for Kelly criterion if needed
                portfolio_metrics = None
                if risk_config.position_sizing_method == "kelly":
                    portfolio_metrics = await self.risk_service.calculate_portfolio_risk_metrics(strategy_id)
                
                # Calculate position size using risk management service (with ATR support)
                position_size_usdt = await self.risk_service.calculate_position_size(
                    strategy_id=strategy_id,
                    account_balance=available_usdt,
                    method=risk_config.position_sizing_method,
                    win_rate=portfolio_metrics.get("win_rate") if portfolio_metrics else None,
                    avg_win=portfolio_metrics.get("avg_win") if portfolio_metrics else None,
                    avg_loss=portfolio_metrics.get("avg_loss") if portfolio_metrics else None,
                    atr=atr,  # Pass ATR for volatility-based sizing
                    current_price=current_price,
                    stop_loss_percent=decision.stop_loss_percent,
                )
                
                # Ensure position size doesn't exceed LLM recommendation
                llm_position_size = available_usdt * decision.position_size_percent
                position_size_usdt = min(position_size_usdt, llm_position_size)
                
                amount = position_size_usdt / current_price  # Convert to base currency
            else:
                # For SELL, need to check existing positions
                position = await self._get_open_position(strategy_id, symbol)
                if not position:
                    return {
                        "executed": False,
                        "reason": "No open position to sell",
                        "decision": decision.model_dump(),
                    }
                amount = position.amount
            
            # Step 3: Execute order
            if decision.action == "BUY":
                order_result = await self.order_service.place_market_order(
                    connection_id=connection_id,
                    symbol=symbol,
                    side="buy",
                    amount=amount,
                    strategy_id=strategy_id,
                )
            elif decision.action == "SELL":
                order_result = await self.order_service.place_market_order(
                    connection_id=connection_id,
                    symbol=symbol,
                    side="sell",
                    amount=amount,
                    strategy_id=strategy_id,
                )
            else:  # HOLD
                return {
                    "executed": False,
                    "reason": "LLM decision is HOLD - no action taken",
                    "decision": decision.model_dump(),
                }
            
            # Step 4: Calculate slippage
            expected_price = current_price
            actual_price = order_result.get("filled_price") or order_result.get("price") or current_price
            slippage = abs(actual_price - expected_price) / expected_price if expected_price > 0 else 0
            
            # Step 5: Create/update trade
            if decision.action == "BUY":
                trade = await self._create_trade(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    buy_order_id=order_result["db_id"],
                    entry_price=actual_price,
                    amount=order_result.get("filled_amount", amount),
                    llm_reasoning=decision.reasoning,
                    llm_confidence=decision.confidence,
                )
                
                # Create position
                position = await self._create_position(
                    trade_id=trade.id,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    amount=trade.amount,
                    entry_price=trade.entry_price,
                )
                
                # Emit trade executed event
                await event_bus.emit(
                    "trade.executed",
                    connection_id=connection_id,
                    strategy_id=strategy_id,
                    data={
                        "trade_id": trade.id,
                        "strategy_id": strategy_id,
                        "symbol": symbol,
                        "side": "buy",
                        "amount": trade.amount,
                        "price": actual_price,
                    }
                )
                
                # Emit portfolio update event
                await event_bus.emit(
                    "portfolio.updated",
                    connection_id=connection_id,
                    data={}
                )
                
            elif decision.action == "SELL":
                # Close existing trade
                position = await self._get_open_position(strategy_id, symbol)
                if position:
                    trade = await self._close_trade(
                        trade_id=position.trade_id,
                        sell_order_id=order_result["db_id"],
                        exit_price=actual_price,
                    )
                    
                    await self._close_position(position.id)
                    
                    # Emit position closed event
                    await event_bus.emit(
                        "position.closed",
                        connection_id=connection_id,
                        strategy_id=strategy_id,
                        data={
                            "position_id": position.id,
                            "symbol": symbol,
                            "final_pnl": trade.pnl or 0.0,
                            "final_pnl_percent": trade.pnl_percent or 0.0,
                        }
                    )
                    
                    # Emit trade executed event
                    await event_bus.emit(
                        "trade.executed",
                        connection_id=connection_id,
                        strategy_id=strategy_id,
                        data={
                            "trade_id": trade.id,
                            "strategy_id": strategy_id,
                            "symbol": symbol,
                            "side": "sell",
                            "amount": trade.amount,
                            "price": actual_price,
                            "realized_pnl": trade.pnl,
                        }
                    )
                    
                    # Update daily loss tracking
                    if trade.pnl:
                        balance = await self.exchange_service.get_balance(connection_id)
                        account_balance = balance.get("usdt", 0.0) + balance.get("btc", 0.0) * current_price
                        await self.risk_service.update_daily_loss(strategy_id, trade.pnl, account_balance)
                    
                    # Emit portfolio update event
                    await event_bus.emit(
                        "portfolio.updated",
                        connection_id=connection_id,
                        data={}
                    )
            
            # Step 6: Validate Risk/Reward Ratio
            risk_reward_ratio = None
            if decision.action == "BUY" and decision.stop_loss_percent and decision.take_profit_percent:
                # R:R = (take_profit_percent) / (stop_loss_percent)
                risk_reward_ratio = decision.take_profit_percent / decision.stop_loss_percent
                
                # Enforce minimum 1:2 R:R
                if risk_reward_ratio < 2.0:
                    logger.warning(
                        "Risk/Reward ratio too low",
                        strategy_id=strategy_id,
                        risk_reward_ratio=risk_reward_ratio,
                        minimum_required=2.0,
                    )
                    return {
                        "executed": False,
                        "reason": f"Risk/Reward ratio {risk_reward_ratio:.2f} below minimum 1:2",
                        "decision": decision.model_dump(),
                    }
            
            # Step 7: Place stop-loss/take-profit orders (use OCO if both specified)
            stop_loss_order = None
            take_profit_order = None
            
            if decision.action == "BUY" and decision.stop_loss_percent and decision.take_profit_percent:
                # Use OCO order if both stop-loss and take-profit are specified
                stop_loss_price = actual_price * (1 - decision.stop_loss_percent)
                take_profit_price = actual_price * (1 + decision.take_profit_percent)
                
                try:
                    oco_result = await self.order_service.place_oco_order(
                        connection_id=connection_id,
                        symbol=symbol,
                        side="sell",
                        amount=amount,
                        stop_price=stop_loss_price,
                        limit_price=take_profit_price,
                        strategy_id=strategy_id,
                    )
                    logger.info(
                        "OCO order placed (stop-loss + take-profit)",
                        strategy_id=strategy_id,
                        oco_group_id=oco_result.get("id"),
                        stop_loss_price=stop_loss_price,
                        take_profit_price=take_profit_price,
                        risk_reward_ratio=risk_reward_ratio,
                    )
                    # OCO creates both orders, mark them appropriately
                    stop_loss_order = {"type": "oco", "group_id": oco_result.get("id")}
                    take_profit_order = {"type": "oco", "group_id": oco_result.get("id")}
                except Exception as e:
                    logger.warning("Failed to place OCO order, falling back to separate orders", error=str(e))
                    # Fall back to separate orders if OCO fails
                    stop_loss_order = None
                    take_profit_order = None
            
            # Fallback: Place separate orders if OCO not used or failed
            if not stop_loss_order and decision.action == "BUY" and decision.stop_loss_percent:
                stop_loss_price = actual_price * (1 - decision.stop_loss_percent)
                try:
                    # CRITICAL: Use STOP_MARKET instead of LIMIT for stop-loss
                    # This ensures execution even if price gaps down
                    stop_loss_order = await self.order_service.place_stop_market_order(
                        connection_id=connection_id,
                        symbol=symbol,
                        side="sell",
                        amount=amount,
                        stop_price=stop_loss_price,
                        strategy_id=strategy_id,
                    )
                    logger.info(
                        "Stop-loss order placed (STOP_MARKET)",
                        strategy_id=strategy_id,
                        order_id=stop_loss_order.get("id"),
                        stop_loss_price=stop_loss_price,
                        risk_reward_ratio=risk_reward_ratio,
                    )
                except Exception as e:
                    logger.warning("Failed to place stop-loss order", error=str(e))
            
            if not take_profit_order and decision.action == "BUY" and decision.take_profit_percent:
                take_profit_price = actual_price * (1 + decision.take_profit_percent)
                try:
                    take_profit_order = await self.order_service.place_limit_order(
                        connection_id=connection_id,
                        symbol=symbol,
                        side="sell",
                        amount=amount,
                        price=take_profit_price,
                        strategy_id=strategy_id,
                    )
                    logger.info(
                        "Take-profit order placed",
                        strategy_id=strategy_id,
                        order_id=take_profit_order.get("id"),
                        take_profit_price=take_profit_price,
                    )
                except Exception as e:
                    logger.warning("Failed to place take-profit order", error=str(e))
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "LLM decision executed",
                strategy_id=strategy_id,
                symbol=symbol,
                action=decision.action,
                order_id=order_result.get("id"),
                slippage_percent=slippage * 100,
                execution_time_ms=execution_time_ms,
            )
            
            return {
                "executed": True,
                "order": order_result,
                "slippage_percent": slippage * 100,
                "execution_time_ms": execution_time_ms,
                "stop_loss_order": stop_loss_order,
                "take_profit_order": take_profit_order,
                "decision": decision.model_dump(),
            }
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to execute LLM decision",
                strategy_id=strategy_id,
                symbol=symbol,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
            raise

    async def _validate_decision(
        self,
        connection_id: int,
        strategy_id: int,
        symbol: str,
        decision: TradingDecision,
        current_price: float,
    ) -> dict[str, Any]:
        """Validate LLM decision before execution."""
        # Get risk config
        risk_config = await self.risk_service.get_risk_config(strategy_id)
        
        # Check confidence threshold
        if decision.confidence < risk_config.min_confidence_threshold:
            return {
                "valid": False,
                "reason": f"Confidence too low: {decision.confidence} < {risk_config.min_confidence_threshold}",
            }
        
        # Check position size against risk config
        if decision.position_size_percent > risk_config.max_position_size_percent:
            return {
                "valid": False,
                "reason": f"Position size exceeds maximum: {decision.position_size_percent} > {risk_config.max_position_size_percent}",
            }
        
        # Check balance for BUY
        if decision.action == "BUY":
            balance = await self.exchange_service.get_balance(connection_id)
            available_usdt = balance.get("usdt", 0.0)
            required_usdt = available_usdt * decision.position_size_percent
            
            if required_usdt < 0.01:  # Minimum order size
                return {"valid": False, "reason": "Position size too small (minimum 0.01 USDT)"}
        
        # Check existing position for SELL
        if decision.action == "SELL":
            position = await self._get_open_position(strategy_id, symbol)
            if not position:
                return {"valid": False, "reason": "No open position to sell"}
        
        return {"valid": True}

    async def _create_trade(
        self,
        strategy_id: int,
        symbol: str,
        buy_order_id: int,
        entry_price: float,
        amount: float,
        llm_reasoning: str,
        llm_confidence: float,
    ) -> Trade:
        """Create a new trade record."""
        trade = Trade(
            strategy_id=strategy_id,
            buy_order_id=buy_order_id,
            symbol=symbol,
            entry_price=entry_price,
            amount=amount,
            status="open",
            llm_reasoning=llm_reasoning,
            llm_confidence=llm_confidence,
        )
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def _close_trade(
        self, trade_id: int, sell_order_id: int, exit_price: float
    ) -> Trade:
        """Close an existing trade."""
        stmt = select(Trade).where(Trade.id == trade_id)
        result = await self.db.execute(stmt)
        trade = result.scalar_one()
        
        trade.sell_order_id = sell_order_id
        trade.exit_price = exit_price
        trade.exit_time = datetime.now(timezone.utc)
        trade.status = "closed"
        
        # Calculate P&L
        trade.pnl = (exit_price - trade.entry_price) * trade.amount
        trade.pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        
        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def _create_position(
        self,
        trade_id: int,
        strategy_id: int,
        symbol: str,
        amount: float,
        entry_price: float,
    ) -> Position:
        """Create a new position record."""
        position = Position(
            trade_id=trade_id,
            strategy_id=strategy_id,
            symbol=symbol,
            amount=amount,
            entry_price=entry_price,
            current_price=entry_price,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
        )
        self.db.add(position)
        await self.db.commit()
        await self.db.refresh(position)
        return position

    async def _close_position(self, position_id: int):
        """Close a position."""
        stmt = select(Position).where(Position.id == position_id)
        result = await self.db.execute(stmt)
        position = result.scalar_one()
        
        await self.db.delete(position)
        await self.db.commit()

    async def _get_open_position(self, strategy_id: int, symbol: str) -> Optional[Position]:
        """Get open position for a strategy and symbol."""
        stmt = select(Position).where(
            Position.strategy_id == strategy_id, Position.symbol == symbol
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

