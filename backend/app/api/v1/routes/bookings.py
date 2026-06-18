"""Управление бронями организатором (ТЗ §4.5). Требуют аутентификации."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.schemas.booking import (
    BookingCancel,
    BookingCreateResponse,
    BookingRead,
    BookingReschedule,
)
from app.services import booking as booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def _get_owned_booking(
    db: DbSession, user_id: uuid.UUID, booking_id: uuid.UUID
) -> Booking:
    obj = await db.get(Booking, booking_id)
    if obj is None or obj.host_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return obj


@router.get("", response_model=list[BookingRead], summary="Мои брони")
async def list_bookings(
    current_user: CurrentUser,
    db: DbSession,
    booking_status: BookingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> list[Booking]:
    query = select(Booking).where(Booking.host_id == current_user.id)
    if booking_status is not None:
        query = query.where(Booking.status == booking_status)
    if date_from is not None:
        query = query.where(
            Booking.start_utc >= datetime.combine(date_from, time.min, tzinfo=UTC)
        )
    if date_to is not None:
        query = query.where(
            Booking.start_utc < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        )
    result = await db.scalars(query.order_by(Booking.start_utc))
    return list(result)


@router.get("/{booking_id}", response_model=BookingRead, summary="Получить бронь")
async def get_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> Booking:
    return await _get_owned_booking(db, current_user.id, booking_id)


@router.post("/{booking_id}/cancel", response_model=BookingRead, summary="Отменить бронь")
async def cancel_booking(
    booking_id: uuid.UUID, data: BookingCancel, current_user: CurrentUser, db: DbSession
) -> Booking:
    booking = await _get_owned_booking(db, current_user.id, booking_id)
    try:
        return await booking_service.cancel_booking(db, booking, reason=data.reason)
    except booking_service.BookingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{booking_id}/reschedule",
    response_model=BookingCreateResponse,
    summary="Перенести бронь",
)
async def reschedule_booking(
    booking_id: uuid.UUID,
    data: BookingReschedule,
    current_user: CurrentUser,
    db: DbSession,
) -> BookingCreateResponse:
    booking = await _get_owned_booking(db, current_user.id, booking_id)
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
        manage_url=f"{settings.public_base_url}/manage/{new_booking.management_token or ''}",
    )
