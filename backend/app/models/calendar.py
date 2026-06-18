"""Подключения внешних календарей (ТЗ §4.6)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CalendarProvider
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.user import User


class CalendarConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", "external_account_id",
            name="uq_calendar_connections_user_provider_account",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[CalendarProvider] = mapped_column(
        enum_column(CalendarProvider), nullable=False
    )
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # tokens: access/refresh-токены (для CalDAV — учётные данные). Хранить шифрованно в проде.
    tokens: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # sync_state: служебное состояние синхронизации (sync token, watermark и т.п.).
    sync_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Календарь, куда писать подтверждённые встречи.
    write_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="calendar_connections")
