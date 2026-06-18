"""Celery-приложение: брокер Redis, периодические задачи (ТЗ §6.1)."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "scheduling_service",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

# Периодические задачи (Celery beat): опрос напоминаний и календарей.
celery_app.conf.beat_schedule = {
    "dispatch-due-notifications": {
        "task": "app.workers.tasks.dispatch_due_notifications",
        "schedule": crontab(minute="*"),  # каждую минуту
    },
    "sync-calendars": {
        "task": "app.workers.tasks.sync_calendars",
        "schedule": crontab(minute="*/2"),  # ТЗ §4.6 КП: блокировка слотов в ≤ 2 мин
    },
    "release-expired-unpaid-bookings": {
        "task": "app.workers.tasks.release_expired_unpaid_bookings",
        "schedule": crontab(minute="*"),  # ТЗ §4.7 КП: освобождать слот по таймауту оплаты
    },
}
