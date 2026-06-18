"""Схемы доступности: расписание (правила по дням) и исключения (ТЗ §4.2)."""

import datetime
import re
import uuid
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _parse_time(value: object) -> datetime.time:
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise ValueError(f"Время должно быть в формате HH:MM (00:00–23:59), получено: {value!r}")
    hour, minute = value.split(":")
    return datetime.time(int(hour), int(minute))


def validate_day_intervals(intervals: object) -> list[list[str]]:
    """Проверяет и нормализует список интервалов одного дня.

    Требования: пары [HH:MM, HH:MM]; начало < конец; внутри дня без пересечений; на выходе
    интервалы отсортированы по началу.
    """
    if not isinstance(intervals, list):
        raise ValueError("Интервалы дня должны быть списком пар [HH:MM, HH:MM]")
    parsed: list[tuple[datetime.time, datetime.time]] = []
    for item in intervals:
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise ValueError(f"Интервал должен быть парой [начало, конец], получено: {item!r}")
        start, end = _parse_time(item[0]), _parse_time(item[1])
        if start >= end:
            raise ValueError(f"Начало интервала должно быть раньше конца: {item!r}")
        parsed.append((start, end))
    parsed.sort(key=lambda pair: pair[0])
    for (_prev_start, prev_end), (cur_start, _cur_end) in zip(parsed, parsed[1:], strict=False):
        if cur_start < prev_end:
            raise ValueError("Интервалы внутри дня не должны пересекаться")
    return [[s.strftime("%H:%M"), e.strftime("%H:%M")] for s, e in parsed]


def _validate_timezone(value: str | None) -> str | None:
    if value is None:
        return value
    try:
        ZoneInfo(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Неизвестный часовой пояс: {value!r}") from exc
    return value


def _validate_rules(value: object) -> dict[str, list[list[str]]]:
    if not isinstance(value, dict):
        raise ValueError("rules должны быть объектом вида {день_недели: [[начало, конец], ...]}")
    normalized: dict[str, list[list[str]]] = {}
    for key, intervals in value.items():
        if key not in WEEKDAYS:
            raise ValueError(f"Недопустимый день недели: {key!r}. Допустимы: {', '.join(WEEKDAYS)}")
        normalized[key] = validate_day_intervals(intervals)
    return normalized


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rules: dict[str, list[list[str]]]
    timezone: str | None
    is_default: bool


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    rules: dict[str, list[list[str]]] | None = None
    timezone: str | None = None

    @field_validator("rules")
    @classmethod
    def _check_rules(cls, v: object) -> object:
        return _validate_rules(v) if v is not None else v

    @field_validator("timezone")
    @classmethod
    def _check_tz(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class ExceptionCreate(BaseModel):
    date: datetime.date
    type: Literal["block", "extra"] = "block"
    interval: list[list[str]] = []

    @model_validator(mode="after")
    def _check(self) -> "ExceptionCreate":
        self.interval = validate_day_intervals(self.interval) if self.interval else []
        if self.type == "extra" and not self.interval:
            raise ValueError("Для исключения типа 'extra' нужно указать непустой interval")
        return self


class ExceptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date | None = None
    type: Literal["block", "extra"] | None = None
    interval: list[list[str]] | None = None

    @field_validator("interval")
    @classmethod
    def _check_interval(cls, v: object) -> object:
        return validate_day_intervals(v) if v else v


class ExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: datetime.date
    type: str
    interval: list[list[str]]
