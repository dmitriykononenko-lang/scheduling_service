"""Типы встреч и кастомные вопросы (ТЗ §4.3)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EventVisibility, LocationType, QuestionFieldType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class EventType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_types"
    __table_args__ = (
        # slug типа уникален в пределах организатора → даёт ссылку domain.ru/<user>/<event-slug>
        UniqueConstraint("user_id", "slug", name="uq_event_types_user_id_slug"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)

    location_type: Mapped[LocationType] = mapped_column(
        enum_column(LocationType), default=LocationType.video, nullable=False
    )
    location_value: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Цена и предоплата (ТЗ §4.3, §4.7). Храним в минорных единицах нельзя из-за Numeric —
    # используем Numeric(10,2) в рублях; currency по умолчанию RUB.
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    requires_prepay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    visibility: Mapped[EventVisibility] = mapped_column(
        enum_column(EventVisibility), default=EventVisibility.public, nullable=False
    )

    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_notice_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_horizon_days: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="event_types")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="event_type",
        cascade="all, delete-orphan",
        order_by="Question.position",
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="event_type")


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Кастомный вопрос гостю при бронировании."""

    __tablename__ = "questions"

    event_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_types.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    field_type: Mapped[QuestionFieldType] = mapped_column(
        enum_column(QuestionFieldType), default=QuestionFieldType.text, nullable=False
    )
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # options: список вариантов для select/checkbox
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event_type: Mapped["EventType"] = relationship(back_populates="questions")
