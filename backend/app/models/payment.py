"""Платежи по броням (ТЗ §4.7)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentProvider, PaymentStatus
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.booking import Booking


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        # Идемпотентность по внешнему id платежа в рамках провайдера (ТЗ §5, §9).
        UniqueConstraint("provider", "external_id", name="uq_payments_provider_external_id"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[PaymentProvider] = mapped_column(enum_column(PaymentProvider), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.pending, index=True, nullable=False
    )
    # external_id — идентификатор платежа на стороне эквайера.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # idempotency_key — ключ для безопасного повтора операции создания платежа.
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # raw_payload — сырой ответ/вебхук провайдера для аудита.
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="payment")
