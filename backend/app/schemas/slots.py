"""Схемы выдачи свободных слотов (ТЗ §4.4)."""

from datetime import datetime

from pydantic import BaseModel


class SlotRead(BaseModel):
    start_utc: datetime
    end_utc: datetime
    start_local: datetime  # в запрошенном поясе гостя


class SlotsResponse(BaseModel):
    event_type_slug: str
    timezone: str  # пояс, в котором посчитан start_local
    slots: list[SlotRead]
