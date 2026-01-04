"""WebSocket endpoint for real-time updates."""

import json
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.core.database import AsyncSessionLocal
from app.core.connection_registry import connection_registry
from app.schemas.websocket import SubscriptionMessage, ErrorMessage
from app.models.exchange import ExchangeConnection

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: int = Query(..., description="Exchange connection ID"),
):
    """
    WebSocket endpoint for real-time trading updates.

    Subscriptions:
    - "prices" - Price updates for symbols
    - "positions" - Position updates (P&L, price changes)
    - "portfolio" - Portfolio value updates
    - "trades" - Trade execution events
    - "strategies" - Strategy status changes

    Example client message:
    {
        "action": "subscribe",
        "channels": ["prices", "positions", "portfolio"]
    }
    """
    # Accept WebSocket connection first
    await websocket.accept()
    
    # Verify connection exists (use a short-lived session, close immediately)
    connection_exists = False
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ExchangeConnection).where(ExchangeConnection.id == connection_id)
            result = await db.execute(stmt)
            connection = result.scalar_one_or_none()
            connection_exists = connection is not None
    except Exception as e:
        logger.error("Error verifying connection", connection_id=connection_id, error=str(e))
        await websocket.close(code=1011, reason="Internal server error")
        return
    
    if not connection_exists:
        await websocket.close(code=1008, reason="Connection not found")
        return

    # Register WebSocket connection
    manager.register_connection(websocket, connection_id)
    
    # Register connection in registry (starts background tasks)
    connection_registry.register(connection_id)

    try:
        # Send welcome message (with error handling)
        try:
            await manager.send_personal_message(
                {
                    "type": "connected",
                    "connection_id": connection_id,
                    "message": "WebSocket connected. Subscribe to channels to receive updates.",
                    "available_channels": ["prices", "positions", "portfolio", "trades", "strategies"],
                },
                websocket,
            )
        except Exception as e:
            # If we can't send welcome message, connection might be closing
            logger.debug("Could not send welcome message", connection_id=connection_id, error=str(e))
            # Continue anyway - client might still be able to receive other messages

        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    error = ErrorMessage(error="Invalid JSON format")
                    await manager.send_personal_message(error.model_dump(mode='json'), websocket)
                    continue

                # Handle subscription messages
                if "action" in message:
                    try:
                        sub_message = SubscriptionMessage(**message)
                        if sub_message.action == "subscribe":
                            for channel in sub_message.channels:
                                manager.subscribe(websocket, channel)
                            await manager.send_personal_message(
                                {
                                    "type": "subscribed",
                                    "channels": sub_message.channels,
                                },
                                websocket,
                            )
                        elif sub_message.action == "unsubscribe":
                            for channel in sub_message.channels:
                                manager.unsubscribe(websocket, channel)
                            await manager.send_personal_message(
                                {
                                    "type": "unsubscribed",
                                    "channels": sub_message.channels,
                                },
                                websocket,
                            )
                    except Exception as e:
                        error = ErrorMessage(error=f"Invalid subscription: {str(e)}")
                        await manager.send_personal_message(error.model_dump(mode='json'), websocket)

                # Handle ping/pong for keepalive
                elif message.get("type") == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected by client", connection_id=connection_id)
                break
            except Exception as e:
                error_str = str(e).lower()
                # Don't log expected disconnection/connection errors
                if not any(keyword in error_str for keyword in ["disconnect", "close", "not connected", "need to call"]):
                    logger.error("WebSocket error", error=str(e), connection_id=connection_id)
                # Try to send error message, but don't fail if websocket is already closed
                try:
                    try:
                        from starlette.websockets import WebSocketState
                        if hasattr(websocket, 'client_state') and websocket.client_state != WebSocketState.DISCONNECTED:
                            error = ErrorMessage(error=f"Server error: {str(e)}")
                            await manager.send_personal_message(error.model_dump(mode='json'), websocket)
                    except (ImportError, AttributeError):
                        # Fallback: try to send anyway
                        error = ErrorMessage(error=f"Server error: {str(e)}")
                        await manager.send_personal_message(error.model_dump(mode='json'), websocket)
                except:
                    pass
                # Break on connection errors
                if "disconnect" in error_str or "close" in error_str:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", connection_id=connection_id)
    except Exception as e:
        error_str = str(e).lower()
        # Only log if it's not a disconnection/connection error
        if not any(keyword in error_str for keyword in ["disconnect", "close", "not connected", "need to call"]):
            logger.error("WebSocket error", connection_id=connection_id, error=str(e))
    finally:
        # Cleanup
        try:
            manager.disconnect(websocket)
        except:
            pass
        # Unregister connection (stops background tasks if no other connections)
        try:
            connection_registry.unregister(connection_id)
        except:
            pass

