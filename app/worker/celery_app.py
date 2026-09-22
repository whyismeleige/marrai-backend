from celery import Celery

from app.config import get_settings

settings = get_settings()

app = Celery(
    "marrai",
    broker=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.TASK_TIME_LIMIT,
    # Early acknowledgement is intentional: a worker crash should not trigger
    # an automatic duplicate crawl of the same site.
    task_acks_late=False,
    task_reject_on_worker_lost=False,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
)