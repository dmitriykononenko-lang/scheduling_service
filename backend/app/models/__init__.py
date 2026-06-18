"""Реэкспорт моделей. Импорт здесь регистрирует таблицы в общем MetaData (важно для Alembic)."""

from app.models.api_key import ApiKey
from app.models.availability import AvailabilityException, AvailabilitySchedule
from app.models.base import Base
from app.models.booking import Booking
from app.models.calendar import CalendarConnection
from app.models.event_type import EventType, Question
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.models.webhook import WebhookEndpoint

__all__ = [
    "ApiKey",
    "AvailabilityException",
    "AvailabilitySchedule",
    "Base",
    "Booking",
    "CalendarConnection",
    "EventType",
    "Notification",
    "Payment",
    "Question",
    "Subscription",
    "User",
    "WebhookEndpoint",
]
