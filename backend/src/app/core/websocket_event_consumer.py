"""WebSocket event consumer - subscribes to events and broadcasts to WebSocket connections."""

import json
import structlog
from typing import Dict, Any

from app.core.events import Event, event_bus
from app.core.websocket import manager
from app.schemas.websocket import (
    PriceUpdateMessage,
    PositionUpdateMessage,
    PortfolioUpdateMessage,
    TradeEventMessage,
    PositionClosedMessage,
    StrategyStatusMessage,
)

logger = structlog.get_logger(__name__)


class WebSocketEventConsumer:
    """Consumes events and broadcasts to WebSocket connections."""
    
    def __init__(self):
        self.running = False
        self._subscriptions: Dict[str, callable] = {}
    
    async def start(self):
        """Start consuming events."""
        if self.running:
            logger.warning("Event consumer already running")
            return
        
        await event_bus.initialize()
        
        # Subscribe to event types
        await event_bus.subscribe("price.updated", self.handle_price_update)
        await event_bus.subscribe("position.updated", self.handle_position_update)
        await event_bus.subscribe("portfolio.updated", self.handle_portfolio_update)
        await event_bus.subscribe("trade.executed", self.handle_trade_executed)
        await event_bus.subscribe("position.closed", self.handle_position_closed)
        await event_bus.subscribe("strategy.status", self.handle_strategy_status)
        
        self.running = True
        logger.info("WebSocket event consumer started")
    
    async def stop(self):
        """Stop consuming events."""
        self.running = False
        logger.info("WebSocket event consumer stopped")
    
    async def handle_price_update(self, event: Event):
        """Handle price update event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = PriceUpdateMessage(
                connection_id=event.connection_id,
                symbol=event.data.get("symbol", ""),
                price=event.data.get("price", 0.0),
                change_24h=event.data.get("change_24h", 0.0),
                volume_24h=event.data.get("volume_24h", 0.0),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="prices"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling price update event", error=str(e))
    
    async def handle_position_update(self, event: Event):
        """Handle position update event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = PositionUpdateMessage(
                connection_id=event.connection_id,
                position_id=event.data.get("position_id"),
                symbol=event.data.get("symbol", ""),
                amount=event.data.get("amount", 0.0),
                entry_price=event.data.get("entry_price", 0.0),
                current_price=event.data.get("current_price", 0.0),
                unrealized_pnl=event.data.get("unrealized_pnl", 0.0),
                unrealized_pnl_percent=event.data.get("unrealized_pnl_percent", 0.0),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="positions"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling position update event", error=str(e))
    
    async def handle_portfolio_update(self, event: Event):
        """Handle portfolio update event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = PortfolioUpdateMessage(
                connection_id=event.connection_id,
                total_value_usdt=event.data.get("total_value_usdt", 0.0),
                cash_usdt=event.data.get("cash_usdt", 0.0),
                invested_usdt=event.data.get("invested_usdt", 0.0),
                unrealized_pnl=event.data.get("unrealized_pnl", 0.0),
                unrealized_pnl_percent=event.data.get("unrealized_pnl_percent", 0.0),
                daily_pnl=event.data.get("daily_pnl", 0.0),
                daily_pnl_percent=event.data.get("daily_pnl_percent", 0.0),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="portfolio"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling portfolio update event", error=str(e))
    
    async def handle_trade_executed(self, event: Event):
        """Handle trade executed event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = TradeEventMessage(
                connection_id=event.connection_id,
                trade_id=event.data.get("trade_id"),
                strategy_id=event.data.get("strategy_id") or event.strategy_id,
                symbol=event.data.get("symbol", ""),
                side=event.data.get("side", ""),
                amount=event.data.get("amount", 0.0),
                price=event.data.get("price", 0.0),
                realized_pnl=event.data.get("realized_pnl"),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="trades"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling trade executed event", error=str(e))
    
    async def handle_position_closed(self, event: Event):
        """Handle position closed event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = PositionClosedMessage(
                connection_id=event.connection_id,
                position_id=event.data.get("position_id"),
                symbol=event.data.get("symbol", ""),
                final_pnl=event.data.get("final_pnl", 0.0),
                final_pnl_percent=event.data.get("final_pnl_percent", 0.0),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="positions"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling position closed event", error=str(e))
    
    async def handle_strategy_status(self, event: Event):
        """Handle strategy status event."""
        try:
            # Check if there are active connections before creating message
            if manager.get_connection_count(event.connection_id) == 0:
                return  # No active connections, skip silently
            
            message = StrategyStatusMessage(
                connection_id=event.connection_id,
                strategy_id=event.data.get("strategy_id") or event.strategy_id,
                status=event.data.get("status", ""),
                performance=event.data.get("performance"),
            )
            await manager.broadcast_to_connection(
                event.connection_id,
                message.model_dump(),
                channel="strategies"
            )
        except Exception as e:
            error_str = str(e).lower()
            # Don't log expected WebSocket errors
            if any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call"]):
                return
            logger.error("Error handling strategy status event", error=str(e))


# Global event consumer instance
websocket_event_consumer = WebSocketEventConsumer()

