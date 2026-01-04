"""Event-driven architecture core - Event Bus implementation."""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
from typing import Any, Callable, Dict, List, Optional, Protocol
import structlog

from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class Event:
    """Event data structure."""
    event_type: str
    connection_id: int
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str
    strategy_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class EventBus(Protocol):
    """Event bus protocol."""

    async def publish(self, event: Event) -> None: ...
    async def subscribe(self, event_type: str, handler: Callable) -> None: ...


class RedisEventBus:
    """Redis-based event bus for distributed event-driven architecture."""

    def __init__(self):
        self.redis = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self._initialized = False
        self._init_lock: Optional[asyncio.Lock] = None

    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return

        # Create lock lazily in the current event loop
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            if not self._initialized:
                self.redis = await get_redis_client()
                self._initialized = True
                logger.info("Event bus initialized")

    async def publish(self, event: Event):
        """Publish event to Redis channel."""
        if not self._initialized:
            await self.initialize()

        try:
            channel = f"events:{event.event_type}"
            message = json.dumps(event.to_dict())
            await self.redis.publish(channel, message)
            logger.debug(
                "Event published",
                event_type=event.event_type,
                connection_id=event.connection_id,
                event_id=event.event_id
            )
        except Exception as e:
            logger.error("Failed to publish event", error=str(e),
                         event_type=event.event_type)
            raise

    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to event type (for in-process subscribers)."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.debug("Subscribed to event type", event_type=event_type)

    async def emit(self, event_type: str, connection_id: int, data: Dict[str, Any], strategy_id: Optional[int] = None):
        """Convenience method to create and publish event."""
        event = Event(
            event_type=event_type,
            connection_id=connection_id,
            data=data,
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            strategy_id=strategy_id
        )
        await self.publish(event)

        # Also notify in-process subscribers
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("Error in event handler",
                                 error=str(e), event_type=event_type)


# Global event bus instance
event_bus = RedisEventBus()
