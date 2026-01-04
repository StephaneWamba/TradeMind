"""Exchange service for managing exchange connections and operations."""

from datetime import datetime, timezone
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt, encrypt
from app.core.redis import get_cache, set_cache
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.core.retry import retry_with_backoff
from app.core.rate_limiter import RateLimiter
from app.services.exchange.adapters.base import BaseExchangeClient
from app.services.exchange.adapters.binance import BinanceClient
from app.models.exchange import Exchange, ExchangeConnection
from app.services.notification.alerting import AlertingService

logger = structlog.get_logger(__name__)

# Circuit breakers for exchange API calls
exchange_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    name="exchange_api"
)

# Rate limiter for exchange API calls (10 requests per second)
exchange_rate_limiter = RateLimiter(
    max_requests=10,
    time_window=1,
    name="exchange_api"
)


class ExchangeService:
    """Service for exchange operations with low latency focus."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.alerting_service = AlertingService()

    async def connect_exchange(self, exchange_name: str, api_key: str, api_secret: str, testnet: bool = False):
        """Connect to an exchange and test the connection."""
        if exchange_name.lower() != "binance":
            raise ValueError(f"Exchange {exchange_name} not supported yet")

        # Create client and test connection
        client = self._create_client(
            exchange_name, api_key, api_secret, testnet=testnet)
        try:
            is_connected = await client.test_connection()
            if not is_connected:
                raise ValueError("Failed to connect to exchange")
        except Exception as e:
            await client.close()
            raise ValueError(f"Connection test failed: {str(e)}")

        # Get or create exchange record
        stmt = select(Exchange).where(Exchange.name == exchange_name.lower())
        result = await self.db.execute(stmt)
        exchange = result.scalar_one_or_none()

        if not exchange:
            exchange = Exchange(name=exchange_name.lower())
            self.db.add(exchange)
            await self.db.flush()

        # Encrypt API credentials
        encrypted_key = encrypt(api_key)
        encrypted_secret = encrypt(api_secret)

        # Create or update connection
        connection = ExchangeConnection(
            exchange_id=exchange.id,
            api_key_encrypted=encrypted_key,
            api_secret_encrypted=encrypted_secret,
            is_testnet=testnet,
            is_active=True,
            last_connected_at=datetime.now(timezone.utc),
        )
        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)

        await client.close()
        return connection

    async def get_client(self, connection_id: int) -> BaseExchangeClient:
        """Get exchange client for a connection with caching."""
        cache_key = f"exchange_client:{connection_id}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug("Exchange client cache hit",
                         connection_id=connection_id)
            # Note: We can't cache the actual client object, so we'll always create a new one
            # But we can cache the connection data to avoid DB queries

        # Get connection from database with exchange join
        stmt = select(ExchangeConnection, Exchange).join(
            Exchange, ExchangeConnection.exchange_id == Exchange.id
        ).where(
            ExchangeConnection.id == connection_id,
            ExchangeConnection.is_active == True
        )
        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError(
                f"Exchange connection {connection_id} not found or inactive")

        connection, exchange = row

        # Decrypt credentials
        api_key = decrypt(connection.api_key_encrypted)
        api_secret = decrypt(connection.api_secret_encrypted)

        # Create client
        client = self._create_client(
            exchange.name,
            api_key,
            api_secret,
            testnet=connection.is_testnet
        )

        # Cache connection data (not the client itself)
        await set_cache(cache_key, {
            "connection_id": connection_id,
            "exchange_name": exchange.name,
            "testnet": connection.is_testnet
        }, ttl=300)

        return client

    def _create_client(self, exchange_name: str, api_key: str, api_secret: str, testnet: bool = False) -> BaseExchangeClient:
        """Create exchange client based on exchange name."""
        if exchange_name.lower() == "binance":
            return BinanceClient(api_key, api_secret, testnet=testnet)
        else:
            raise ValueError(f"Exchange {exchange_name} not supported")

    async def test_connection(self, connection_id: int) -> bool:
        """Test exchange connection with resilience patterns."""
        async def _test():
            await exchange_rate_limiter.acquire()
            client = await self.get_client(connection_id)
            try:
                return await client.test_connection()
            finally:
                await client.close()

        async def _test_with_retry():
            return await retry_with_backoff(
                _test,
                max_retries=3,
                initial_delay=1.0
            )

        try:
            result = await exchange_circuit_breaker.call(_test_with_retry)
            return result
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker open for exchange",
                         connection_id=connection_id)
            await self.alerting_service.send_alert(
                subject="Exchange Connection Failure",
                message=f"Circuit breaker opened for exchange connection {connection_id}. Exchange API may be down.",
                priority="high"
            )
            raise
        except Exception as e:
            logger.error("Exchange connection test failed",
                         connection_id=connection_id, error=str(e))
            await self.alerting_service.send_alert(
                subject="Exchange Connection Test Failed",
                message=f"Failed to test connection {connection_id}: {str(e)}",
                priority="normal"
            )
            raise
