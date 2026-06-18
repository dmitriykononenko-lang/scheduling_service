"""API-ключи для публичного API (ТЗ §4.10, §9)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), default="API key", nullable=False)
    # Храним только SHA-256 хеш ключа; сам ключ показывается пользователю один раз.
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # Префикс для отображения в UI (напр. "sk_abcd…").
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # scopes: ограниченные права ключа (ТЗ §9: ключи с ограниченными scopes).
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")
