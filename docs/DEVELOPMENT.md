# Development Guide

## Project Structure

```
backend/src/app/
├── domain/              # Business logic (pure, no infrastructure)
│   ├── trading/        # Position management
│   ├── market/         # Indicators, orderbook
│   ├── risk/           # Risk management
│   └── backtest/       # Backtesting engine
├── services/            # Application services
│   ├── llm/            # LLM services (Grok, Tavily)
│   ├── exchange/       # Exchange integration
│   │   └── adapters/  # Exchange adapters (Binance)
│   ├── monitoring/     # Order monitoring, reconciliation
│   └── notification/   # Email alerts
├── api/                 # REST API endpoints
│   └── v1/
│       └── endpoints/  # Route handlers
├── core/               # Infrastructure
│   ├── database.py    # DB connection & session
│   ├── redis.py        # Redis client
│   ├── websocket.py   # WebSocket manager
│   └── events.py      # Event bus
├── models/             # SQLAlchemy models
├── schemas/            # Pydantic schemas
└── workers/            # Celery tasks
```

## Code Organization Principles

### Domain Layer

- **Pure business logic** - No database, no HTTP, no external services
- **Testable** - Easy to unit test
- **Reusable** - Can be used in different contexts

**Example:**
```python
# domain/risk/management.py
class RiskManagementService:
    async def calculate_position_size(...) -> float:
        # Pure calculation logic
        pass
```

### Services Layer

- **Orchestration** - Coordinates domain logic
- **Infrastructure access** - Database, external APIs
- **Application-specific** - Tied to use cases

**Example:**
```python
# services/execution.py
class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_service = RiskManagementService(db)
    
    async def execute_llm_decision(...):
        # Orchestrate: validate risk, place order, create records
        pass
```

## Adding New Features

### 1. Add New Exchange Adapter

1. Create adapter in `services/exchange/adapters/`:
```python
# services/exchange/adapters/kraken.py
from app.services.exchange.adapters.base import BaseExchangeClient

class KrakenClient(BaseExchangeClient):
    async def test_connection(self) -> bool:
        # Implement
        pass
    # ... implement other methods
```

2. Register in `services/exchange/service.py`:
```python
def _create_client(self, exchange_name: str, ...):
    if exchange_name.lower() == "kraken":
        return KrakenClient(api_key, api_secret)
    # ...
```

### 2. Add New Technical Indicator

1. Add to `domain/market/indicators.py`:
```python
def calculate_new_indicator(prices: list[float]) -> float:
    # Implementation
    pass
```

2. Include in `calculate_indicators()`:
```python
def calculate_indicators(...) -> dict:
    return {
        # ... existing indicators
        "new_indicator": calculate_new_indicator(prices),
    }
```

### 3. Add New API Endpoint

1. Create endpoint in `api/v1/endpoints/`:
```python
# api/v1/endpoints/new_feature.py
router = APIRouter()

@router.get("/new-endpoint")
async def new_endpoint(db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
```

2. Register in `api/v1/router.py`:
```python
from app.api.v1.endpoints import new_feature

api_router.include_router(
    new_feature.router, prefix="/new-feature", tags=["new-feature"]
)
```

## Database Migrations

### Create Migration

```bash
cd backend
alembic revision -m "description"
```

### Edit Migration

Edit the generated file in `alembic/versions/`:

```python
def upgrade():
    op.add_column('table_name', sa.Column('new_column', sa.String()))

def downgrade():
    op.drop_column('table_name', 'new_column')
```

### Apply Migration

```bash
alembic upgrade head
```

## Testing

### Unit Tests

Test domain logic in isolation:

```python
# tests/domain/test_risk.py
async def test_calculate_position_size():
    service = RiskManagementService(None)  # No DB needed
    size = await service.calculate_position_size(...)
    assert size > 0
```

### Integration Tests

Test services with database:

```python
# tests/services/test_execution.py
async def test_execute_llm_decision(db_session):
    service = ExecutionService(db_session)
    result = await service.execute_llm_decision(...)
    assert result["status"] == "executed"
```

## Code Style

- **Type Hints**: Use everywhere
- **Async/Await**: Prefer async for I/O
- **Error Handling**: Use specific exceptions
- **Logging**: Use `structlog` with context
- **Docstrings**: Document public methods

**Example:**
```python
async def calculate_position_size(
    self,
    strategy_id: int,
    account_balance: float,
    method: str = "fixed",
) -> float:
    """
    Calculate position size using specified method.
    
    Args:
        strategy_id: Strategy ID
        account_balance: Current account balance
        method: Position sizing method
        
    Returns:
        Position size in USDT
    """
    # Implementation
```

## Debugging

### Enable Debug Logging

Set in `.env`:
```
LOG_LEVEL=DEBUG
```

### Database Query Logging

Set in `.env`:
```
DATABASE_ECHO=true
```

### Check Celery Tasks

```bash
# List active tasks
docker exec -it trademind-worker celery -A app.workers.celery_app inspect active

# Check task result
docker exec -it trademind-worker celery -A app.workers.celery_app result <task_id>
```

## Performance Optimization

### Database

- Use `selectinload()` for eager loading
- Close sessions promptly
- Use connection pooling (configured in `database.py`)

### Caching

- Cache market data (5s TTL)
- Cache exchange clients (300s TTL)
- Use Redis for shared cache

### Async Operations

- Use `asyncio.gather()` for parallel operations
- Avoid blocking I/O in async functions
- Use connection pooling for external APIs

## Common Patterns

### Service Initialization

```python
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.other_service = OtherService(db)
```

### Error Handling

```python
try:
    result = await operation()
except SpecificError as e:
    logger.error("Operation failed", error=str(e))
    raise HTTPException(status_code=400, detail=str(e))
```

### Event Emission

```python
from app.core.events import event_bus

await event_bus.emit("trade_executed", {
    "trade_id": trade.id,
    "symbol": trade.symbol,
    "pnl": trade.pnl,
})
```

## Deployment Checklist

- [ ] Set `DEBUG=false`
- [ ] Configure production CORS origins
- [ ] Set up proper secrets management
- [ ] Configure database backups
- [ ] Set up monitoring/alerting
- [ ] Test email alerts
- [ ] Verify WebSocket connections
- [ ] Check Celery worker health
- [ ] Review log levels

