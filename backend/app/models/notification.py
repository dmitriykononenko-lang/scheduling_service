"""Уведомления по броням (ТЗ §4.9)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.booking import Booking


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_column(NotificationChannel), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(enum_column(NotificationType), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        enum_column(NotificationStatus),
        default=NotificationStatus.scheduled,
        index=True,
        nullable=False,
    )
    # Когда уведомление должно быть отправлено (UTC). Планировщик опрашивает по этому полю.
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="notifications")
