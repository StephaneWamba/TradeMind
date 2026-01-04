# API Reference

Base URL: `http://localhost:5000/api/v1`

All endpoints return JSON. WebSocket endpoint: `/ws`

## Authentication

Currently, API keys are managed per exchange connection. Future versions will include user authentication.

## Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/health/detailed` | Detailed health status |

### Exchange

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/exchange/connections` | List all connections |
| `POST` | `/exchange/connect` | Connect to exchange |
| `GET` | `/exchange/status?connection_id={id}` | Get connection status |
| `GET` | `/exchange/balance?connection_id={id}` | Get account balance |

**Connect Exchange:**
```json
POST /api/v1/exchange/connect
{
  "exchange_name": "binance",
  "api_key": "your_api_key",
  "api_secret": "your_secret",
  "testnet": false
}
```

### Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/market/ticker?symbol={symbol}&connection_id={id}` | Get ticker price |
| `GET` | `/market/tickers?symbols={symbols}&connection_id={id}` | Get multiple tickers |
| `GET` | `/market/indicators?symbol={symbol}&connection_id={id}&timeframe={tf}` | Get technical indicators |

**Indicators Response:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "rsi": 45.2,
  "macd": {
    "macd": 12.5,
    "signal": 10.2,
    "histogram": 2.3
  },
  "atr": 1250.5,
  "signal": "NEUTRAL"
}
```

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/orders/market` | Place market order |
| `POST` | `/orders/limit` | Place limit order |
| `GET` | `/orders/list?connection_id={id}` | List orders |
| `GET` | `/trades/list?connection_id={id}` | List trades |

**Market Order:**
```json
POST /api/v1/orders/market
{
  "connection_id": 1,
  "symbol": "BTC/USDT",
  "side": "buy",
  "amount": 0.001
}
```

### Strategy

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/strategy` | List strategies |
| `POST` | `/strategy` | Create strategy |
| `GET` | `/strategy/{id}` | Get strategy details |
| `PUT` | `/strategy/{id}` | Update strategy |
| `DELETE` | `/strategy/{id}` | Delete strategy |

### LLM Strategy

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/llm-strategy/analyze` | Analyze market (unstructured) |
| `POST` | `/llm-strategy/analyze-structured` | Analyze market (structured) |

**Analyze Market:**
```json
POST /api/v1/llm-strategy/analyze
{
  "connection_id": 1,
  "symbol": "BTC/USDT",
  "strategy_id": 1
}
```

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/execution/execute?connection_id={id}&strategy_id={id}&symbol={symbol}` | Execute LLM decision |

This endpoint:
1. Analyzes market using LLM
2. Gets structured trading decision
3. Validates risk limits
4. Executes order
5. Creates trade/position records

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/portfolio/overview?connection_id={id}` | Portfolio overview |
| `GET` | `/portfolio/value?connection_id={id}` | Portfolio value history |
| `GET` | `/portfolio/performance?connection_id={id}` | Performance metrics |

### Risk Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/risk/config/{strategy_id}` | Get risk config |
| `PUT` | `/risk/config/{strategy_id}` | Update risk config |
| `GET` | `/risk/daily-loss/{strategy_id}` | Get daily loss status |
| `GET` | `/risk/circuit-breaker/{strategy_id}` | Get circuit breaker status |
| `POST` | `/risk/circuit-breaker/{strategy_id}/reset` | Reset circuit breaker |
| `POST` | `/risk/emergency-stop` | Emergency stop all strategies |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/metrics/overview?connection_id={id}` | Business metrics overview |
| `GET` | `/metrics/performance?connection_id={id}` | Performance metrics |
| `GET` | `/metrics/risk?connection_id={id}` | Risk metrics |
| `GET` | `/metrics/trade-stats?connection_id={id}` | Trade statistics |

### Backtest

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/backtest/run` | Run backtest (async) |
| `GET` | `/backtest/quick` | Quick backtest (last N days) |
| `GET` | `/backtest/status/{backtest_id}` | Get backtest status |
| `GET` | `/backtest/list` | List backtests |
| `POST` | `/backtest/cancel/{backtest_id}` | Cancel backtest |

**Run Backtest:**
```
POST /api/v1/backtest/run?strategy_id=1&connection_id=1&symbol=BTC/USDT&start_date=2024-01-01&end_date=2024-01-31&timeframe=1h&initial_balance=10000
```

**Response:**
```json
{
  "backtest_id": 123,
  "status": "pending",
  "message": "Backtest started. Use /api/v1/backtest/status/123 to check progress."
}
```

### Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/automation/trigger?strategy_id={id}&symbol={symbol}` | Manually trigger automation |
| `GET` | `/automation/status` | Get automation status |

### WebSocket

**Endpoint:** `/ws?connection_id={id}`

**Subscribe:**
```json
{
  "action": "subscribe",
  "channels": ["prices", "positions", "portfolio", "trades"]
}
```

**Channels:**
- `prices` - Price updates
- `positions` - Position updates (P&L)
- `portfolio` - Portfolio value updates
- `trades` - Trade execution events
- `strategies` - Strategy status changes

**Message Format:**
```json
{
  "channel": "prices",
  "data": {
    "symbol": "BTC/USDT",
    "price": 45000.5,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

- Exchange API: 10 requests/second (enforced)
- LLM API: No explicit limit (Grok rate limits apply)
- General API: No limit (consider adding for production)

## Pagination

List endpoints support pagination:

```
GET /api/v1/backtest/list?limit=20&offset=0
```

