"""Работа с расписаниями доступности (ТЗ §4.2)."""

import copy
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import AvailabilitySchedule
from app.models.user import User

# Дефолтное расписание нового пользователя: будни 10:00–18:00, выходные пустые.
DEFAULT_RULES: dict[str, list[list[str]]] = {
    "mon": [["10:00", "18:00"]],
    "tue": [["10:00", "18:00"]],
    "wed": [["10:00", "18:00"]],
    "thu": [["10:00", "18:00"]],
    "fri": [["10:00", "18:00"]],
}


def make_default_schedule(**kwargs: object) -> AvailabilitySchedule:
    """Создаёт (несохранённый) объект дефолтного расписания. kwargs: user_id или user."""
    return AvailabilitySchedule(
        name="Основное",
        rules=copy.deepcopy(DEFAULT_RULES),
        is_default=True,
        **kwargs,
    )


async def get_default_schedule(db: AsyncSession, user_id: uuid.UUID) -> AvailabilitySchedule:
    """Возвращает дефолтное расписание пользователя.

    Приоритет: `is_default=True` → самое раннее → ленивое создание (сейфти для аккаунтов,
    созданных до появления авто-создания при регистрации).
    """
    schedule = await db.scalar(
        select(AvailabilitySchedule).where(
            AvailabilitySchedule.user_id == user_id,
            AvailabilitySchedule.is_default.is_(True),
        )
    )
    if schedule is not None:
        return schedule

    schedule = await db.scalar(
        select(AvailabilitySchedule)
        .where(AvailabilitySchedule.user_id == user_id)
        .order_by(AvailabilitySchedule.created_at)
        .limit(1)
    )
    if schedule is not None:
        return schedule

    schedule = make_default_schedule(user_id=user_id)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


def resolve_timezone(schedule: AvailabilitySchedule, user: User) -> str:
    """Эффективный пояс расписания: собственный пояс расписания или пояс пользователя."""
    return schedule.timezone or user.timezone
