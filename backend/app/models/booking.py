"""Модель брони — центральная сущность (ТЗ §4.4, §4.5)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BookingStatus
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.event_type import EventType
    from app.models.notification import Notification
    from app.models.payment import Payment


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # ТЗ §7: индекс по (host_id, start_utc). Ограничение на пересечение броней
        # одного хоста реализовано EXCLUDE-констрейнтом в миграции (btree_gist).
        Index("ix_bookings_host_start", "host_id", "start_utc"),
    )

    event_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_types.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    invitee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invitee_contact: Mapped[str] = mapped_column(String(255), nullable=False)
    invitee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invitee_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus), default=BookingStatus.confirmed, index=True, nullable=False
    )
    location_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # answers: ответы гостя на кастомные вопросы {question_id: value}
    answers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Если бронь — результат переноса, ссылается на исходную.
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )

    event_type: Mapped["EventType"] = relationship(back_populates="bookings")
    payment: Mapped["Payment | None"] = relationship(
        back_populates="booking", cascade="all, delete-orphan", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Booking {self.id} {self.status} {self.start_utc.isoformat()}>"
