"""Схемы типов встреч."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EventVisibility, LocationType


class EventTypeBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    duration_minutes: int = Field(default=30, ge=5, le=1440)
    color: str | None = Field(default=None, max_length=16)
    location_type: LocationType = LocationType.video
    location_value: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    requires_prepay: bool = False
    visibility: EventVisibility = EventVisibility.public
    buffer_before_minutes: int = Field(default=0, ge=0, le=1440)
    buffer_after_minutes: int = Field(default=0, ge=0, le=1440)
    min_notice_minutes: int = Field(default=0, ge=0)
    max_horizon_days: int = Field(default=60, ge=1, le=365)
    daily_limit: int | None = Field(default=None, ge=1)


class EventTypeCreate(EventTypeBase):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


class EventTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    color: str | None = Field(default=None, max_length=16)
    location_type: LocationType | None = None
    location_value: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    requires_prepay: bool | None = None
    visibility: EventVisibility | None = None
    buffer_before_minutes: int | None = Field(default=None, ge=0, le=1440)
    buffer_after_minutes: int | None = Field(default=None, ge=0, le=1440)
    min_notice_minutes: int | None = Field(default=None, ge=0)
    max_horizon_days: int | None = Field(default=None, ge=1, le=365)
    daily_limit: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class EventTypeRead(EventTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    slug: str
    is_active: bool
