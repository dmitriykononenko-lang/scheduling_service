"""Схемы бронирования (ТЗ §4.4, §4.5)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import BookingStatus


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Время должно содержать часовой пояс (например, '2026-07-01T10:00:00Z')")
    return value.astimezone(UTC)


def _validate_tz(value: str | None) -> str | None:
    if value is None:
        return value
    try:
        ZoneInfo(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Неизвестный часовой пояс: {value!r}") from exc
    return value


class BookingCreate(BaseModel):
    start_utc: datetime
    invitee_name: str = Field(min_length=1, max_length=255)
    invitee_contact: str = Field(min_length=1, max_length=255)
    invitee_email: EmailStr | None = None
    invitee_timezone: str | None = Field(default=None, max_length=64)
    answers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_utc")
    @classmethod
    def _check_start(cls, v: datetime) -> datetime:
        return _require_utc(v)

    @field_validator("invitee_timezone")
    @classmethod
    def _check_tz(cls, v: str | None) -> str | None:
        return _validate_tz(v)


class BookingReschedule(BaseModel):
    start_utc: datetime

    @field_validator("start_utc")
    @classmethod
    def _check_start(cls, v: datetime) -> datetime:
        return _require_utc(v)


class BookingCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type_id: uuid.UUID
    host_id: uuid.UUID
    invitee_name: str
    invitee_contact: str
    invitee_email: str | None
    invitee_timezone: str | None
    start_utc: datetime
    end_utc: datetime
    status: BookingStatus
    location_url: str | None
    answers: dict[str, Any]
    rescheduled_from_id: uuid.UUID | None
    created_at: datetime


class BookingManageRead(BookingRead):
    """Бронь по токену управления + контекст для гостевой страницы (ТЗ §4.5).

    Поля host_*/event_* нужны странице `/manage`: показать встречу и подгрузить слоты
    для переноса (слот-эндпоинт ключуется по слугам организатора и типа встречи).
    """

    host_name: str
    host_slug: str
    host_timezone: str
    event_title: str
    event_slug: str
    event_duration_minutes: int
    price: Decimal | None
    currency: str
    requires_prepay: bool


class BookingCreateResponse(BaseModel):
    booking: BookingRead
    management_token: str
    manage_url: str
