"""Управление типами встреч организатором (ТЗ §4.3)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.event_type import EventType
from app.schemas.event_type import EventTypeCreate, EventTypeRead, EventTypeUpdate

router = APIRouter(prefix="/event-types", tags=["event-types"])


async def _get_owned(db: DbSession, user_id: uuid.UUID, event_type_id: uuid.UUID) -> EventType:
    obj = await db.get(EventType, event_type_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип встречи не найден")
    return obj


@router.get("", response_model=list[EventTypeRead], summary="Мои типы встреч")
async def list_event_types(current_user: CurrentUser, db: DbSession) -> list[EventType]:
    result = await db.scalars(
        select(EventType)
        .where(EventType.user_id == current_user.id)
        .order_by(EventType.created_at)
    )
    return list(result)


@router.post(
    "",
    response_model=EventTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать тип встречи",
)
async def create_event_type(
    data: EventTypeCreate, current_user: CurrentUser, db: DbSession
) -> EventType:
    obj = EventType(user_id=current_user.id, **data.model_dump())
    db.add(obj)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Тип встречи с таким slug уже существует",
        ) from exc
    await db.refresh(obj)
    return obj


@router.get("/{event_type_id}", response_model=EventTypeRead, summary="Получить тип встречи")
async def get_event_type(
    event_type_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> EventType:
    return await _get_owned(db, current_user.id, event_type_id)


@router.patch("/{event_type_id}", response_model=EventTypeRead, summary="Обновить тип встречи")
async def update_event_type(
    event_type_id: uuid.UUID,
    data: EventTypeUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> EventType:
    obj = await _get_owned(db, current_user.id, event_type_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete(
    "/{event_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тип встречи",
)
async def delete_event_type(
    event_type_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    obj = await _get_owned(db, current_user.id, event_type_id)
    await db.delete(obj)
    await db.commit()
