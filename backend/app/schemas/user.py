"""Схемы пользователя."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class UserPublic(BaseModel):
    """Публичная карточка организатора (для страницы domain.ru/<slug>)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    timezone: str


class UserRead(BaseModel):
    """Полные данные пользователя для личного кабинета."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    slug: str
    timezone: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
