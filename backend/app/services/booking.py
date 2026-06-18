"""Бизнес-логика броней: создание, атомарный перенос, отмена (ТЗ §4.4, §4.5)."""

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event_type import EventType, Question
from app.schemas.booking import BookingCreate
from app.services.slots import compute_available_slots

# Статусы, из которых бронь можно отменить/перенести.
_MODIFIABLE = (BookingStatus.confirmed, BookingStatus.pending_payment)


class BookingValidationError(Exception):
    """Некорректные данные брони (например, не отвечены обязательные вопросы) → 422."""


class SlotUnavailableError(Exception):
    """Запрошенный слот недоступен (занят, вне расписания, нарушает min_notice) → 409."""


class BookingConflictError(Exception):
    """Гонка на уровне БД: слот заняли параллельно (EXCLUDE-ограничение) → 409."""


def generate_management_token() -> str:
    return secrets.token_urlsafe(32)


async def _load_questions(db: AsyncSession, event_type_id: uuid.UUID) -> Sequence[Question]:
    result = await db.scalars(
        select(Question).where(Question.event_type_id == event_type_id)
    )
    return list(result)


def _validate_answers(questions: Sequence[Question], answers: dict) -> None:
    for question in questions:
        value = answers.get(str(question.id))
        if question.required and (value is None or value == "" or value == []):
            raise BookingValidationError(f"Не отвечен обязательный вопрос: {question.label!r}")
        if (
            value is not None
            and question.field_type.value == "select"
            and question.options
            and value not in question.options
        ):
            raise BookingValidationError(
                f"Недопустимый вариант ответа на вопрос {question.label!r}"
            )


async def _slot_is_available(
    db: AsyncSession, event_type: EventType, start_utc: datetime, now: datetime
) -> bool:
    """Слот всё ещё доступен? Считаем слоты вокруг даты и проверяем точное совпадение."""
    range_from = (start_utc - timedelta(days=1)).date()
    range_to = (start_utc + timedelta(days=1)).date()
    slots = await compute_available_slots(
        db, event_type, range_from=range_from, range_to=range_to, invitee_tz="UTC", now=now
    )
    return any(slot.start_utc == start_utc for slot in slots)


def _assert_modifiable(booking: Booking) -> None:
    # Точка расширения под политики отмены/переноса по типу встречи (ТЗ §4.5) — пока без окон.
    if booking.status not in _MODIFIABLE:
        raise BookingValidationError("Эту бронь нельзя изменить (она отменена или завершена)")


def _status_for(event_type: EventType) -> BookingStatus:
    return (
        BookingStatus.pending_payment if event_type.requires_prepay else BookingStatus.confirmed
    )


async def create_booking(
    db: AsyncSession,
    event_type: EventType,
    data: BookingCreate,
    *,
    now: datetime | None = None,
) -> Booking:
    now = now or datetime.now(UTC)
    questions = await _load_questions(db, event_type.id)
    _validate_answers(questions, data.answers)

    if not await _slot_is_available(db, event_type, data.start_utc, now):
        raise SlotUnavailableError("Выбранный слот недоступен")

    end_utc = data.start_utc + timedelta(minutes=event_type.duration_minutes)
    booking = Booking(
        event_type_id=event_type.id,
        host_id=event_type.user_id,
        invitee_name=data.invitee_name,
        invitee_contact=data.invitee_contact,
        invitee_email=data.invitee_email,
        invitee_timezone=data.invitee_timezone,
        start_utc=data.start_utc,
        end_utc=end_utc,
        status=_status_for(event_type),
        answers=data.answers,
        management_token=generate_management_token(),
    )
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BookingConflictError("Слот уже занят") from exc
    await db.refresh(booking)
    return booking


async def reschedule_booking(
    db: AsyncSession,
    booking: Booking,
    new_start_utc: datetime,
    *,
    now: datetime | None = None,
) -> Booking:
    """Атомарный перенос: освобождает старый слот и занимает новый (ТЗ §4.5 КП).

    Порядок важен: сначала переводим старую бронь в `rescheduled` (она выходит из активного
    набора EXCLUDE и освобождает слот), затем вставляем новую. Всё в одной транзакции —
    при коллизии с третьей бронью откатываемся, старая бронь остаётся нетронутой.
    """
    now = now or datetime.now(UTC)
    _assert_modifiable(booking)
    if new_start_utc == booking.start_utc:
        raise BookingValidationError("Новое время совпадает с текущим")

    event_type = await db.get(EventType, booking.event_type_id)
    if event_type is None:
        raise BookingValidationError("Тип встречи не найден")

    old_id = booking.id
    old_status = booking.status
    # Освобождаем старый слот в рамках транзакции и фиксируем во flush, чтобы ре-валидация
    # и вставка видели его уже неактивным.
    booking.status = BookingStatus.rescheduled
    booking.canceled_at = now
    await db.flush()

    if not await _slot_is_available(db, event_type, new_start_utc, now):
        # Откатываем освобождение старой брони — перенос не состоялся.
        await db.rollback()
        raise SlotUnavailableError("Новый слот недоступен")

    end_utc = new_start_utc + timedelta(minutes=event_type.duration_minutes)
    new_booking = Booking(
        event_type_id=event_type.id,
        host_id=event_type.user_id,
        invitee_name=booking.invitee_name,
        invitee_contact=booking.invitee_contact,
        invitee_email=booking.invitee_email,
        invitee_timezone=booking.invitee_timezone,
        start_utc=new_start_utc,
        end_utc=end_utc,
        status=_status_for(event_type),
        answers=booking.answers,
        rescheduled_from_id=old_id,
        management_token=generate_management_token(),
    )
    db.add(new_booking)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # Возвращаем старую бронь в исходный статус — перенос не удался.
        restored = await db.get(Booking, old_id)
        if restored is not None:
            restored.status = old_status
            restored.canceled_at = None
            await db.commit()
        raise BookingConflictError("Новый слот уже занят") from exc
    await db.refresh(new_booking)
    return new_booking


async def cancel_booking(
    db: AsyncSession,
    booking: Booking,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> Booking:
    now = now or datetime.now(UTC)
    _assert_modifiable(booking)
    booking.status = BookingStatus.canceled
    booking.canceled_at = now
    booking.cancellation_reason = reason
    await db.commit()
    await db.refresh(booking)
    return booking
