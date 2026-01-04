"""Celery application for background task processing."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "trademind",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks", "app.workers.backtest_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes (default)
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        # Autonomous trading - runs every 15 minutes
        'autonomous-trading-every-15min': {
            'task': 'autonomous_trading',
            'schedule': 900.0,  # Every 15 minutes (900 seconds)
            'options': {'expires': 900},
        },
    },
)
