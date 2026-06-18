"""Фоновые задачи. На этапе каркаса — заглушки с правильными сигнатурами и ретраями.

Реальная логика (отправка email/Telegram, опрос календарей, доставка webhooks с HMAC
и экспоненциальными ретраями) добавляется в соответствующих фичах MVP/Ф2.
"""

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.dispatch_due_notifications")
def dispatch_due_notifications() -> dict[str, int]:
    """Находит уведомления со scheduled_at <= now и status=scheduled, отправляет их.

    ТЗ §4.9: напоминания уходят в заданное время по email и Telegram с учётом пояса.
    """
    logger.info("task.dispatch_due_notifications.tick")
    # TODO(MVP §4.9): выбрать due-уведомления и отправить через провайдеров.
    return {"dispatched": 0}


@celery_app.task(name="app.workers.tasks.sync_calendars")
def sync_calendars() -> dict[str, int]:
    """Опрашивает подключённые календари и обновляет занятость (ТЗ §4.6)."""
    logger.info("task.sync_calendars.tick")
    # TODO(MVP §4.6): для активных CalendarConnection подтянуть busy/free.
    return {"synced": 0}


@celery_app.task(name="app.workers.tasks.release_expired_unpaid_bookings")
def release_expired_unpaid_bookings() -> dict[str, int]:
    """Освобождает слоты броней с предоплатой, не оплаченных в срок (ТЗ §4.7 КП).

    Логика (добавляется в срезе платежей): найти брони в статусе `pending_payment` старше TTL
    без успешного Payment → перевести в `canceled`, чтобы слот вернулся в выдачу.
    """
    logger.info("task.release_expired_unpaid_bookings.tick")
    # TODO(срез §4.7): отменять просроченные pending_payment без успешной оплаты.
    return {"released": 0}


@celery_app.task(
    name="app.workers.tasks.deliver_webhook",
    bind=True,
    max_retries=6,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def deliver_webhook(self, endpoint_id: str, event: str, payload: dict) -> None:  # type: ignore[no-untyped-def]
    """Доставляет событие на webhook-эндпоинт с подписью HMAC и ретраями (ТЗ §4.10).

    На этапе каркаса — только логирование; HTTP-доставка добавляется в Ф2.
    """
    logger.info("task.deliver_webhook", endpoint_id=endpoint_id, event=event)
    # TODO(Ф2 §4.10): POST на endpoint.url с заголовком подписи HMAC; при ошибке self.retry().
