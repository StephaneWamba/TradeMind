"""Connection registry to track active connections and manage background tasks."""

import asyncio
from typing import Set, Dict, Tuple
import structlog

from app.workers.tasks import update_prices_task, update_portfolio_task, monitor_orders_task, reconcile_orders_task

logger = structlog.get_logger(__name__)


class ConnectionRegistry:
    """Tracks active connections and manages periodic background tasks."""
    
    def __init__(self):
        self.active_connections: Set[int] = set()
        self._periodic_tasks: Dict[int, Tuple[asyncio.Task, ...]] = {}
        self._price_update_interval = 5.0  # seconds
        self._portfolio_update_interval = 30.0  # seconds
        self._running = False
    
    def register(self, connection_id: int):
        """Register a new connection."""
        if connection_id not in self.active_connections:
            self.active_connections.add(connection_id)
            logger.info("Connection registered", connection_id=connection_id, total=len(self.active_connections))
            
            # Start periodic tasks for this connection
            self._start_periodic_tasks(connection_id)
    
    def unregister(self, connection_id: int):
        """Unregister a connection."""
        if connection_id in self.active_connections:
            self.active_connections.discard(connection_id)
            logger.info("Connection unregistered", connection_id=connection_id, total=len(self.active_connections))
            
            # Stop periodic tasks for this connection
            self._stop_periodic_tasks(connection_id)
    
    def _start_periodic_tasks(self, connection_id: int):
        """Start periodic background tasks for a connection."""
        async def price_update_loop():
            while connection_id in self.active_connections:
                try:
                    # Schedule Celery task
                    update_prices_task.delay(connection_id)
                    await asyncio.sleep(self._price_update_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in price update loop", connection_id=connection_id, error=str(e))
                    await asyncio.sleep(self._price_update_interval)
        
        async def portfolio_update_loop():
            while connection_id in self.active_connections:
                try:
                    # Schedule Celery task
                    update_portfolio_task.delay(connection_id)
                    await asyncio.sleep(self._portfolio_update_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in portfolio update loop", connection_id=connection_id, error=str(e))
                    await asyncio.sleep(self._portfolio_update_interval)
        
        async def order_monitor_loop():
            while connection_id in self.active_connections:
                try:
                    # Schedule order monitoring every 30 seconds
                    monitor_orders_task.delay(connection_id)
                    await asyncio.sleep(30.0)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in order monitor loop", connection_id=connection_id, error=str(e))
                    await asyncio.sleep(30.0)
        
        async def order_reconcile_loop():
            while connection_id in self.active_connections:
                try:
                    # Schedule order reconciliation every 5 minutes
                    reconcile_orders_task.delay(connection_id)
                    await asyncio.sleep(300.0)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in order reconcile loop", connection_id=connection_id, error=str(e))
                    await asyncio.sleep(300.0)
        
        # Start all loops
        price_task = asyncio.create_task(price_update_loop())
        portfolio_task = asyncio.create_task(portfolio_update_loop())
        monitor_task = asyncio.create_task(order_monitor_loop())
        reconcile_task = asyncio.create_task(order_reconcile_loop())
        self._periodic_tasks[connection_id] = (price_task, portfolio_task, monitor_task, reconcile_task)
    
    def _stop_periodic_tasks(self, connection_id: int):
        """Stop periodic tasks for a connection."""
        if connection_id in self._periodic_tasks:
            tasks = self._periodic_tasks.pop(connection_id)
            for task in tasks:
                task.cancel()
            logger.info("Periodic tasks stopped", connection_id=connection_id)
    
    def get_active_connections(self) -> Set[int]:
        """Get set of active connection IDs."""
        return self.active_connections.copy()
    
    def is_registered(self, connection_id: int) -> bool:
        """Check if connection is registered."""
        return connection_id in self.active_connections


# Global connection registry
connection_registry = ConnectionRegistry()

