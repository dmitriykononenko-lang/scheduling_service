"""Управление доступностью организатором: расписание и исключения (ТЗ §4.2)."""

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.availability import AvailabilityException, AvailabilitySchedule
from app.schemas.availability import (
    ExceptionCreate,
    ExceptionRead,
    ExceptionUpdate,
    ScheduleRead,
    ScheduleUpdate,
)
from app.services.availability import get_default_schedule

router = APIRouter(prefix="/availability", tags=["availability"])


async def _get_owned_exception(
    db: DbSession, user_id: uuid.UUID, exception_id: uuid.UUID
) -> AvailabilityException:
    """Возвращает исключение, проверяя, что его расписание принадлежит пользователю."""
    obj = await db.scalar(
        select(AvailabilityException)
        .join(AvailabilitySchedule)
        .where(
            AvailabilityException.id == exception_id,
            AvailabilitySchedule.user_id == user_id,
        )
    )
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Исключение не найдено")
    return obj


@router.get("/schedule", response_model=ScheduleRead, summary="Моё расписание (по умолчанию)")
async def get_schedule(current_user: CurrentUser, db: DbSession) -> AvailabilitySchedule:
    return await get_default_schedule(db, current_user.id)


@router.patch("/schedule", response_model=ScheduleRead, summary="Обновить расписание")
async def update_schedule(
    data: ScheduleUpdate, current_user: CurrentUser, db: DbSession
) -> AvailabilitySchedule:
    schedule = await get_default_schedule(db, current_user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.get(
    "/exceptions",
    response_model=list[ExceptionRead],
    summary="Исключения расписания (выходные/доп. часы)",
)
async def list_exceptions(
    current_user: CurrentUser,
    db: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[AvailabilityException]:
    schedule = await get_default_schedule(db, current_user.id)
    query = select(AvailabilityException).where(
        AvailabilityException.schedule_id == schedule.id
    )
    if date_from is not None:
        query = query.where(AvailabilityException.date >= date_from)
    if date_to is not None:
        query = query.where(AvailabilityException.date <= date_to)
    result = await db.scalars(query.order_by(AvailabilityException.date))
    return list(result)


@router.post(
    "/exceptions",
    response_model=ExceptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить исключение",
)
async def create_exception(
    data: ExceptionCreate, current_user: CurrentUser, db: DbSession
) -> AvailabilityException:
    schedule = await get_default_schedule(db, current_user.id)
    obj = AvailabilityException(
        schedule_id=schedule.id,
        date=data.date,
        type=data.type,
        interval=data.interval,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch(
    "/exceptions/{exception_id}",
    response_model=ExceptionRead,
    summary="Изменить исключение",
)
async def update_exception(
    exception_id: uuid.UUID,
    data: ExceptionUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AvailabilityException:
    obj = await _get_owned_exception(db, current_user.id, exception_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete(
    "/exceptions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить исключение",
)
async def delete_exception(
    exception_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    obj = await _get_owned_exception(db, current_user.id, exception_id)
    await db.delete(obj)
    await db.commit()
