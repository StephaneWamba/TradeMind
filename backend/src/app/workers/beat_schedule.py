"""Celery Beat schedule configuration for periodic tasks."""

from celery.schedules import crontab

# Beat schedule for periodic tasks
beat_schedule = {
    # Autonomous trading - runs every 15 minutes
    'autonomous-trading-every-15min': {
        'task': 'autonomous_trading',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'expires': 900},  # Expire after 15 minutes
    },
    # Can add more schedules here:
    # 'autonomous-trading-hourly': {
    #     'task': 'autonomous_trading',
    #     'schedule': crontab(minute=0),  # Every hour at :00
    # },
}

