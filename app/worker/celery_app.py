from celery import Celery

from app.config import get_settings

settings = get_settings()

app = Celery(
    'jobs', 
    broker=settings.REDIS_URL
)

app.autodiscover_tasks(['app.worker'])

app.conf.task_serializer = 'json'