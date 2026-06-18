"""Модель пользователя (организатор/админ)."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.api_key import ApiKey
    from app.models.availability import AvailabilitySchedule
    from app.models.calendar import CalendarConnection
    from app.models.event_type import EventType
    from app.models.subscription import Subscription
    from app.models.webhook import WebhookEndpoint


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Публичная ссылка вида domain.ru/<slug> (ТЗ §4.1) — обязательна и уникальна.
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole), default=UserRole.host, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Привязка Telegram-чата для уведомлений (ТЗ §4.9).
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- Связи ---
    availability_schedules: Mapped[list["AvailabilitySchedule"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    event_types: Mapped[list["EventType"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    calendar_connections: Mapped[list["CalendarConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    webhook_endpoints: Mapped[list["WebhookEndpoint"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} slug={self.slug}>"
