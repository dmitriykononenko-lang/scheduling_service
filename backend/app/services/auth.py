"""Сервис аутентификации: регистрация и проверка учётных данных."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.availability import make_default_schedule
from app.services.slug import generate_unique_user_slug


class EmailAlreadyExistsError(Exception):
    """Пользователь с таким email уже зарегистрирован."""


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    email = data.email.lower()
    if await get_user_by_email(db, email):
        raise EmailAlreadyExistsError(email)

    slug = await generate_unique_user_slug(db, data.name or email.split("@")[0])
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        name=data.name,
        slug=slug,
        timezone=data.timezone,
    )
    # Сразу даём пользователю дефолтное расписание (Пн–Пт 10–18) в той же транзакции.
    user.availability_schedules.append(make_default_schedule())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
