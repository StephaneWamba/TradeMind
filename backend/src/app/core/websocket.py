"""WebSocket connection manager for real-time updates."""

import json
import structlog
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""

    def __init__(self):
        # Map of connection_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # Map of WebSocket -> Set of subscribed channels
        self.subscriptions: Dict[WebSocket, Set[str]] = defaultdict(set)
        # Map of WebSocket -> connection_id
        self.connection_ids: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, connection_id: int):
        """Accept a new WebSocket connection (deprecated - use register_connection)."""
        await websocket.accept()
        self.register_connection(websocket, connection_id)

    def register_connection(self, websocket: WebSocket, connection_id: int):
        """Register a WebSocket connection (assumes websocket is already accepted)."""
        self.active_connections[connection_id].add(websocket)
        self.connection_ids[websocket] = connection_id
        logger.info(
            "WebSocket connected",
            connection_id=connection_id,
            total_connections=len(self.active_connections[connection_id]),
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        connection_id = self.connection_ids.pop(websocket, None)
        if connection_id:
            self.active_connections[connection_id].discard(websocket)
            if not self.active_connections[connection_id]:
                del self.active_connections[connection_id]
        self.subscriptions.pop(websocket, None)
        logger.info(
            "WebSocket disconnected",
            connection_id=connection_id,
        )

    def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a connection to a channel."""
        self.subscriptions[websocket].add(channel)
        logger.debug(
            "Subscribed to channel",
            channel=channel,
            connection_id=self.connection_ids.get(websocket),
        )

    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a connection from a channel."""
        self.subscriptions[websocket].discard(channel)
        logger.debug(
            "Unsubscribed from channel",
            channel=channel,
            connection_id=self.connection_ids.get(websocket),
        )

    def is_subscribed(self, websocket: WebSocket, channel: str) -> bool:
        """Check if a connection is subscribed to a channel."""
        return channel in self.subscriptions.get(websocket, set())

    def _is_connected(self, websocket: WebSocket) -> bool:
        """Check if WebSocket is still connected."""
        try:
            # Check if websocket is in our tracking
            if websocket not in self.connection_ids:
                return False
            # Check WebSocket application state
            # FastAPI WebSocket has client_state attribute
            if hasattr(websocket, 'client_state'):
                try:
                    from starlette.websockets import WebSocketState
                    return websocket.client_state != WebSocketState.DISCONNECTED
                except (ImportError, AttributeError):
                    # Fallback if WebSocketState not available
                    return True
            return True
        except Exception:
            return False

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        # Check if websocket is registered
        if websocket not in self.connection_ids:
            # Silently return - this is expected when connections haven't been established
            return

        try:
            # Check WebSocket state before sending
            try:
                from starlette.websockets import WebSocketState
                if hasattr(websocket, 'client_state'):
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        self.disconnect(websocket)
                        return
                    # Also check if it's not in CONNECTED state
                    if websocket.client_state != WebSocketState.CONNECTED:
                        self.disconnect(websocket)
                    return
            except (ImportError, AttributeError):
                # Fallback if WebSocketState not available
                pass

            # Convert datetime objects to ISO strings for JSON serialization
            import json
            from datetime import datetime

            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            # Ensure message is JSON serializable
            message_str = json.dumps(message, default=json_serial)
            await websocket.send_text(message_str)
        except Exception as e:
            error_str = str(e).lower() if str(e) else ""
            error_type = type(e).__name__

            # Silently handle connection errors (expected when clients disconnect)
            # Also handle empty errors (often indicate connection issues)
            if (not error_str or
                any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call", "connection", "websocket"]) or
                    any(keyword in error_type.lower() for keyword in ["connection", "websocket", "disconnect"])):
                try:
                    self.disconnect(websocket)
                except:
                    pass
                # Don't log these - they're expected
                return
            else:
                # Only log unexpected errors with actual error messages
                if error_str:
                    logger.warning("Failed to send message",
                                   error=str(e), error_type=error_type)
                try:
                    self.disconnect(websocket)
                except:
                    pass

    async def broadcast_to_connection(
        self, connection_id: int, message: dict, channel: Optional[str] = None
    ):
        """Broadcast a message to all connections for a specific connection_id."""
        connections = self.active_connections.get(connection_id, set()).copy()
        if not connections:
            # No active connections - silently return (this is normal)
            return

        disconnected = set()
        for websocket in connections:
            # Check if websocket is registered
            if websocket not in self.connection_ids:
                disconnected.add(websocket)
                continue

            # Check WebSocket state before attempting to send
            try:
                from starlette.websockets import WebSocketState
                if hasattr(websocket, 'client_state'):
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        disconnected.add(websocket)
                        continue
                    # Also check if it's not in CONNECTED state
                    if websocket.client_state != WebSocketState.CONNECTED:
                        disconnected.add(websocket)
                        continue
            except (ImportError, AttributeError):
                # Fallback if WebSocketState not available - try to send anyway
                pass

            # If channel specified, only send to subscribed connections
            if channel and not self.is_subscribed(websocket, channel):
                continue

            try:
                # Double-check WebSocket state right before sending
                try:
                    from starlette.websockets import WebSocketState
                    if hasattr(websocket, 'client_state'):
                        if websocket.client_state != WebSocketState.CONNECTED:
                            disconnected.add(websocket)
                            continue
                except (ImportError, AttributeError):
                    pass

                # Convert datetime objects to ISO strings for JSON serialization
                import json
                from datetime import datetime

                def json_serial(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")

                message_str = json.dumps(message, default=json_serial)
                await websocket.send_text(message_str)
            except Exception as e:
                error_str = str(e).lower() if str(e) else ""
                error_type = type(e).__name__

                # Silently handle connection errors (they're expected when clients disconnect)
                # Also handle empty errors
                if (not error_str or
                    any(keyword in error_str for keyword in ["not connected", "close", "disconnect", "need to call", "connection", "websocket"]) or
                        any(keyword in error_type.lower() for keyword in ["connection", "websocket", "disconnect"])):
                    disconnected.add(websocket)
                    # Don't log these - they're expected
                else:
                    # Only log unexpected errors with actual messages
                    if error_str:
                        logger.warning("Failed to broadcast message",
                                       error=str(e), error_type=error_type, connection_id=connection_id)
                    disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            try:
                self.disconnect(ws)
            except:
                pass

    async def broadcast_to_all(self, message: dict, channel: Optional[str] = None):
        """Broadcast a message to all active connections."""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections.copy())

        disconnected = set()
        for websocket in all_connections:
            # Check if websocket is registered
            if websocket not in self.connection_ids:
                disconnected.add(websocket)
                continue

            # Check WebSocket state
            try:
                from starlette.websockets import WebSocketState
                if hasattr(websocket, 'client_state') and websocket.client_state == WebSocketState.DISCONNECTED:
                    disconnected.add(websocket)
                    continue
            except (ImportError, AttributeError):
                # Fallback if WebSocketState not available
                pass

            # If channel specified, only send to subscribed connections
            if channel and not self.is_subscribed(websocket, channel):
                continue

            try:
                # Convert datetime objects to ISO strings for JSON serialization
                import json
                from datetime import datetime

                def json_serial(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")

                message_str = json.dumps(message, default=json_serial)
                await websocket.send_text(message_str)
            except Exception as e:
                error_str = str(e).lower()
                # Only log if it's not a connection closed error (which is expected)
                if "not connected" not in error_str and "close" not in error_str and "disconnect" not in error_str:
                    logger.warning("Failed to broadcast message", error=str(e))
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)

    def get_connection_count(self, connection_id: Optional[int] = None) -> int:
        """Get the number of active connections."""
        if connection_id:
            return len(self.active_connections.get(connection_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
