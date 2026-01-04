# Railway Deployment Setup

## Prerequisites

1. Install Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login to Railway:
```bash
railway login
```

## Setup Services

### 1. Create PostgreSQL Service

```bash
railway add postgresql
```

This will create a PostgreSQL service and set `DATABASE_URL` automatically.

### 2. Create Redis Service

```bash
railway add redis
```

This will create a Redis service and set `REDIS_URL` automatically.

### 3. Set Environment Variables

```bash
# LLM
railway variables set GROK_API_KEY=your_grok_api_key_here

# Binance (Testnet)
railway variables set BINANCE_TESTNET=true
railway variables set BINANCE_API_KEY=your_binance_api_key_here
railway variables set BINANCE_API_SECRET=your_binance_api_secret_here

# Email
railway variables set RESEND_API_KEY=your_resend_api_key_here
railway variables set EMAIL_FROM=onboarding@resend.dev
railway variables set ALERT_EMAIL_RECEIVER=your_email@example.com

# Tavily
railway variables set TAVILY_API_KEY=your_tavily_api_key_here

# Application
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set ENVIRONMENT=production
```

### 4. Update Database URL Format

Railway provides PostgreSQL URL in format `postgresql://...`, but we need `postgresql+asyncpg://`. Set it manually:

```bash
# Get the DATABASE_URL from Railway
railway variables

# Update it to use asyncpg driver
railway variables set DATABASE_URL="postgresql+asyncpg://[your-railway-db-url]"
```

### 5. Update Redis URLs

Railway provides `REDIS_URL`, but we also need `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`:

```bash
# Get REDIS_URL from Railway
railway variables

# Set Celery URLs (use different Redis databases)
railway variables set CELERY_BROKER_URL="[REDIS_URL]/1"
railway variables set CELERY_RESULT_BACKEND="[REDIS_URL]/2"
```

### 6. Update CORS Origins

Add your Vercel frontend URL:

```bash
railway variables set CORS_ORIGINS='["http://localhost:3000","https://*.vercel.app","https://*.railway.app"]'
```

## Deploy Backend

```bash
# Make sure you're in the project root
railway up
```

## Create Worker Service

For Celery worker, create a separate service:

1. In Railway dashboard, create a new service
2. Use the same Dockerfile
3. Set environment variable: `CELERY_WORKER=true`
4. Set start command: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2`

## Create Beat Service (Optional)

For Celery Beat scheduler:

1. Create another service
2. Use the same Dockerfile
3. Set start command: `celery -A app.workers.celery_app beat --loglevel=info`

## Verify Deployment

```bash
# Check service status
railway status

# View logs
railway logs

# Open service
railway open
```

## Database Migrations

Migrations run automatically on startup (see Dockerfile). To run manually:

```bash
railway run alembic upgrade head
```

