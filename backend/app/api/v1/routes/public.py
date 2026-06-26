"""Публичные эндпоинты страницы записи (ТЗ §4.4, §4.5). Без аутентификации.

Гостевое управление бронью — под зарезервированным префиксом `/public/manage/{token}`,
чтобы не конфликтовать с профилем организатора `/public/{user_slug}` (см. RESERVED_SLUGS).
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.core.config import settings
from app.models.booking import Booking
from app.models.enums import EventVisibility
from app.models.event_type import EventType
from app.models.user import User
from app.schemas.booking import (
    BookingCancel,
    BookingCreate,
    BookingCreateResponse,
    BookingRead,
    BookingReschedule,
)
from app.schemas.event_type import EventTypePublicDetail, EventTypeRead
from app.schemas.slots import SlotRead, SlotsResponse
from app.schemas.user import UserPublic
from app.services import booking as booking_service
from app.services.slots import compute_available_slots

router = APIRouter(prefix="/public", tags=["public"])

_MAX_SLOTS_SPAN_DAYS = 62


async def _get_host(db: DbSession, user_slug: str) -> User:
    host = await db.scalar(select(User).where(User.slug == user_slug, User.is_active.is_(True)))
    if host is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организатор не найден")
    return host


async def _get_public_event_type(
    db: DbSession, host: User, event_slug: str, *, load_questions: bool = False
) -> EventType:
    stmt = select(EventType).where(
        EventType.user_id == host.id,
        EventType.slug == event_slug,
        EventType.is_active.is_(True),
    )
    if load_questions:
        # Eager-load для async: страница записи читает event_type.questions (ленивый доступ
        # вне greenlet упал бы). Relationship уже отсортирован по Question.position.
        stmt = stmt.options(selectinload(EventType.questions))
    obj = await db.scalar(stmt)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип встречи не найден")
    return obj


async def _get_booking_by_token(db: DbSession, token: str) -> Booking:
    obj = await db.scalar(select(Booking).where(Booking.management_token == token))
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return obj


def _validate_tz(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Неизвестный часовой пояс: {tz!r}",
        ) from exc
    return tz


def _manage_url(token: str) -> str:
    return f"{settings.public_base_url}/manage/{token}"


# --- Профиль и типы встреч ---


@router.get("/{user_slug}", response_model=UserPublic, summary="Публичный профиль организатора")
async def public_profile(user_slug: str, db: DbSession) -> User:
    return await _get_host(db, user_slug)


@router.get(
    "/{user_slug}/event-types",
    response_model=list[EventTypeRead],
    summary="Публичные типы встреч организатора",
)
async def public_event_types(user_slug: str, db: DbSession) -> list[EventType]:
    host = await _get_host(db, user_slug)
    result = await db.scalars(
        select(EventType).where(
            EventType.user_id == host.id,
            EventType.is_active.is_(True),
            # Скрытые (unlisted) не показываем в общем списке профиля (ТЗ §4.3 КП).
            EventType.visibility == EventVisibility.public,
        )
    )
    return list(result)


@router.get(
    "/{user_slug}/event-types/{event_slug}",
    response_model=EventTypePublicDetail,
    summary="Тип встречи по прямой ссылке",
)
async def public_event_type_detail(user_slug: str, event_slug: str, db: DbSession) -> EventType:
    host = await _get_host(db, user_slug)
    # По прямой ссылке доступен и скрытый (unlisted) тип — главное, что активный.
    # Вопросы анкеты нужны странице записи, чтобы отрисовать форму (ТЗ §4.4).
    return await _get_public_event_type(db, host, event_slug, load_questions=True)


# --- Свободные слоты ---


@router.get(
    "/{user_slug}/event-types/{event_slug}/slots",
    response_model=SlotsResponse,
    summary="Свободные слоты типа встречи",
)
async def public_slots(
    user_slug: str,
    event_slug: str,
    db: DbSession,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tz: str | None = Query(default=None),
) -> SlotsResponse:
    host = await _get_host(db, user_slug)
    event_type = await _get_public_event_type(db, host, event_slug)

    range_from = date_from or date.today()
    range_to = date_to or (range_from + timedelta(days=30))
    if range_to < range_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="'from' должно быть ≤ 'to'"
        )
    if (range_to - range_from).days > _MAX_SLOTS_SPAN_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Диапазон не должен превышать {_MAX_SLOTS_SPAN_DAYS} дней",
        )

    invitee_tz = _validate_tz(tz) if tz else host.timezone
    slots = await compute_available_slots(
        db, event_type, range_from=range_from, range_to=range_to, invitee_tz=invitee_tz
    )
    return SlotsResponse(
        event_type_slug=event_type.slug,
        timezone=invitee_tz,
        slots=[
            SlotRead(start_utc=s.start_utc, end_utc=s.end_utc, start_local=s.start_local)
            for s in slots
        ],
    )


# --- Создание брони гостем ---


@router.post(
    "/{user_slug}/event-types/{event_slug}/bookings",
    response_model=BookingCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Забронировать слот",
)
async def public_create_booking(
    user_slug: str, event_slug: str, data: BookingCreate, db: DbSession
) -> BookingCreateResponse:
    host = await _get_host(db, user_slug)
    event_type = await _get_public_event_type(db, host, event_slug)
    try:
        booking = await booking_service.create_booking(db, event_type, data)
    except booking_service.BookingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (booking_service.SlotUnavailableError, booking_service.BookingConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return BookingCreateResponse(
        booking=BookingRead.model_validate(booking),
        management_token=booking.management_token or "",
        manage_url=_manage_url(booking.management_token or ""),
    )


# --- Гостевое управление бронью по токену ---


@router.get(
    "/manage/{token}", response_model=BookingRead, summary="Бронь по токену управления"
)
async def guest_get_booking(token: str, db: DbSession) -> Booking:
    return await _get_booking_by_token(db, token)


@router.post(
    "/manage/{token}/cancel", response_model=BookingRead, summary="Отменить бронь (гость)"
)
async def guest_cancel_booking(token: str, data: BookingCancel, db: DbSession) -> Booking:
    booking = await _get_booking_by_token(db, token)
    try:
        return await booking_service.cancel_booking(db, booking, reason=data.reason)
    except booking_service.BookingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/manage/{token}/reschedule",
    response_model=BookingCreateResponse,
    summary="Перенести бронь (гость)",
)
async def guest_reschedule_booking(
    token: str, data: BookingReschedule, db: DbSession
) -> BookingCreateResponse:
    booking = await _get_booking_by_token(db, token)
    try:
        new_booking = await booking_service.reschedule_booking(db, booking, data.start_utc)
    except booking_service.BookingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (booking_service.SlotUnavailableError, booking_service.BookingConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return BookingCreateResponse(
        booking=BookingRead.model_validate(new_booking),
        management_token=new_booking.management_token or "",
        manage_url=_manage_url(new_booking.management_token or ""),
    )
