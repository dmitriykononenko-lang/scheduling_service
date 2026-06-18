"""Модели доступности: расписания и исключения (ТЗ §4.2)."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AvailabilitySchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Набор правил рабочего времени. У пользователя их может быть несколько (Ф2)."""

    __tablename__ = "availability_schedules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), default="Основное", nullable=False)
    # rules: JSON со структурой по дням недели и интервалам, напр.:
    # {"mon": [["10:00","18:00"]], "tue": [["10:00","13:00"],["14:00","18:00"]], ...}
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="availability_schedules")
    exceptions: Mapped[list["AvailabilityException"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class AvailabilityException(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Разовое исключение: блокировка дня или дополнительные часы."""

    __tablename__ = "availability_exceptions"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("availability_schedules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # type: "block" (выходной/блокировка) | "extra" (дополнительные часы)
    type: Mapped[str] = mapped_column(String(16), default="block", nullable=False)
    # interval: список пар [["10:00","14:00"]]; для full-day block — пустой список
    interval: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    schedule: Mapped["AvailabilitySchedule"] = relationship(back_populates="exceptions")
