# Setup Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- Node.js 18+ (for frontend development)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/StephaneWamba/TradeMind
cd TradeMind
```

### 2. Environment Configuration

Create `.env` file in project root:

```bash
# Exchange API (Binance)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret
BINANCE_TESTNET=false

# LLM (Grok)
GROK_API_KEY=your_grok_api_key
GROK_MODEL=grok-2-1212
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000

# Tavily (Web/X Search)
TAVILY_API_KEY=your_tavily_api_key

# Email Alerts (Resend)
RESEND_API_KEY=your_resend_api_key
ALERT_EMAIL_RECEIVER=your_email@example.com
ALERT_EMAIL_SENDER=onboarding@resend.dev

# Application
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:

- PostgreSQL (port 5435)
- Redis (port 6382)
- Backend API (port 5000)
- Celery Worker + Beat

### 4. Verify Installation

```bash
# Check backend health
curl http://localhost:5000/health

# Check API docs
open http://localhost:5000/docs
```

## Configuration Reference

### Environment Variables

| Variable               | Default                    | Description                   |
| ---------------------- | -------------------------- | ----------------------------- |
| `BINANCE_API_KEY`      | -                          | Binance API key (required)    |
| `BINANCE_API_SECRET`   | -                          | Binance API secret (required) |
| `BINANCE_TESTNET`      | `false`                    | Use Binance testnet           |
| `GROK_API_KEY`         | -                          | Grok API key (required)       |
| `GROK_MODEL`           | `grok-2-1212`              | Grok model name               |
| `TAVILY_API_KEY`       | -                          | Tavily API key (optional)     |
| `RESEND_API_KEY`       | -                          | Resend API key (optional)     |
| `ALERT_EMAIL_RECEIVER` | `wambstephane@gmail.com`   | Alert recipient               |
| `DATABASE_URL`         | `postgresql+asyncpg://...` | PostgreSQL connection         |
| `REDIS_URL`            | `redis://redis:6379/0`     | Redis connection              |
| `LOG_LEVEL`            | `INFO`                     | Logging level                 |

### Trading Parameters

| Variable                        | Default      | Description           |
| ------------------------------- | ------------ | --------------------- |
| `MIN_POSITION_SIZE`             | `0.00000001` | Minimum position size |
| `MAX_POSITION_SIZE_PERCENT`     | `0.02`       | Max 2% per trade      |
| `DEFAULT_POSITION_SIZE_PERCENT` | `0.01`       | Default 1% per trade  |
| `MAX_DAILY_LOSS_PERCENT`        | `0.05`       | Max 5% daily loss     |
| `MAX_DRAWDOWN_PERCENT`          | `0.10`       | Max 10% drawdown      |

## Database Setup

Database schema is auto-created on first startup. For manual migrations:

```bash
# Enter backend container
docker exec -it trademind-backend bash

# Run migrations
cd /app
alembic upgrade head
```

## Frontend Setup (Development)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

## Production Deployment

### Docker Compose Production

1. Update `docker-compose.yml`:

   - Remove volume mounts
   - Set `DEBUG=false`
   - Configure proper secrets

2. Build and deploy:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Specific Settings

| Environment | DEBUG   | LOG_LEVEL | CORS_ORIGINS       |
| ----------- | ------- | --------- | ------------------ |
| Development | `true`  | `DEBUG`   | `localhost:*`      |
| Production  | `false` | `INFO`    | Production domains |

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker logs trademind-postgres

# Test connection
docker exec -it trademind-postgres psql -U postgres -d trademind
```

### Redis Connection Issues

```bash
# Check Redis logs
docker logs trademind-redis

# Test connection
docker exec -it trademind-redis redis-cli ping
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker logs trademind-worker

# Verify Celery is running
docker exec -it trademind-worker celery -A app.workers.celery_app inspect active
```

### API Not Responding

```bash
# Check backend logs
docker logs trademind-backend

# Verify health endpoint
curl http://localhost:5000/health
```

## Next Steps

1. [Connect Exchange](API.md#exchange-endpoints) - Add Binance connection
2. [Create Strategy](API.md#strategy-endpoints) - Set up trading strategy
3. [Run Backtest](API.md#backtest-endpoints) - Test strategy on historical data
4. [Enable Automation](API.md#automation-endpoints) - Start autonomous trading
