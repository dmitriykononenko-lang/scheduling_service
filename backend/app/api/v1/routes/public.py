"""Публичные эндпоинты страницы записи (ТЗ §4.4). Без аутентификации."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.enums import EventVisibility
from app.models.event_type import EventType
from app.models.user import User
from app.schemas.event_type import EventTypeRead
from app.schemas.user import UserPublic

router = APIRouter(prefix="/public", tags=["public"])


async def _get_host(db: DbSession, user_slug: str) -> User:
    host = await db.scalar(select(User).where(User.slug == user_slug, User.is_active.is_(True)))
    if host is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организатор не найден")
    return host


@router.get(
    "/{user_slug}",
    response_model=UserPublic,
    summary="Публичный профиль организатора",
)
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
    response_model=EventTypeRead,
    summary="Тип встречи по прямой ссылке",
)
async def public_event_type_detail(
    user_slug: str, event_slug: str, db: DbSession
) -> EventType:
    host = await _get_host(db, user_slug)
    # По прямой ссылке доступен и скрытый (unlisted) тип — главное, что активный.
    obj = await db.scalar(
        select(EventType).where(
            EventType.user_id == host.id,
            EventType.slug == event_slug,
            EventType.is_active.is_(True),
        )
    )
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип встречи не найден")
    return obj
