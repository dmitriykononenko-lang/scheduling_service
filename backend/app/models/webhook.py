"""Webhook-эндпоинты для внешних интеграций (ТЗ §4.10)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class WebhookEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "webhook_endpoints"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    # secret — для подписи HMAC доставляемых событий (ТЗ §4.10 Ф2, §9).
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    # events: список подписанных событий, напр.
    # ["booking.created","booking.canceled","booking.rescheduled","payment.succeeded"]
    events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="webhook_endpoints")
