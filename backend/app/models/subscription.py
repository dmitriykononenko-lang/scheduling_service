"""Подписки и тарифы (ТЗ §4.14)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubscriptionPeriod, SubscriptionPlan, SubscriptionStatus
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        enum_column(SubscriptionPlan), default=SubscriptionPlan.free, nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_column(SubscriptionStatus), default=SubscriptionStatus.trialing, nullable=False
    )
    period: Mapped[SubscriptionPeriod | None] = mapped_column(
        enum_column(SubscriptionPeriod), nullable=True
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")
