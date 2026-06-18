"""Расчёт свободных слотов (ТЗ §4.2, §4.4).

`build_slots` — чистая функция (без БД), вся арифметика в UTC, окна строятся в поясе хоста,
шаги идут по локальным настенным часам (корректно для переходов на летнее/зимнее время).
`compute_available_slots` подгружает данные из БД и вызывает `build_slots`.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import AvailabilityException
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event_type import EventType
from app.models.user import User
from app.services.availability import get_default_schedule, resolve_timezone

WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Статусы броней, которые занимают слот (резерв под оплату тоже занимает).
ACTIVE_STATUSES = (BookingStatus.confirmed, BookingStatus.pending_payment)

Interval = tuple[datetime, datetime]  # UTC, tz-aware
TimeRange = tuple[time, time]


@dataclass(frozen=True)
class Slot:
    start_utc: datetime
    end_utc: datetime
    start_local: datetime  # в поясе гостя, только для отображения


@dataclass(frozen=True)
class DayException:
    date: date
    type: str  # "block" | "extra"
    interval: list[list[str]]


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _parse_pair(pair: list[str]) -> TimeRange:
    return _parse_time(pair[0]), _parse_time(pair[1])


def _merge(intervals: list[TimeRange]) -> list[TimeRange]:
    """Сортирует и объединяет пересекающиеся/смежные интервалы одного дня."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    out = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = out[-1]
        if start <= last_end:
            out[-1] = (last_start, max(last_end, end))
        else:
            out.append((start, end))
    return out


def _subtract(intervals: list[TimeRange], block_start: time, block_end: time) -> list[TimeRange]:
    """Вырезает [block_start, block_end) из каждого интервала."""
    out: list[TimeRange] = []
    for start, end in intervals:
        if block_end <= start or block_start >= end:
            out.append((start, end))
            continue
        if block_start > start:
            out.append((start, block_start))
        if block_end < end:
            out.append((block_end, end))
    return out


def _day_windows(
    day: date,
    rules: dict[str, list[list[str]]],
    blocks_full: set[date],
    block_intervals: dict[date, list[TimeRange]],
    extra_intervals: dict[date, list[TimeRange]],
) -> list[TimeRange]:
    """Итоговые рабочие окна дня (host-local) с учётом исключений."""
    if day in blocks_full:
        return []
    key = WEEKDAYS[day.weekday()]
    base = [_parse_pair(p) for p in rules.get(key, [])]
    base.extend(extra_intervals.get(day, []))
    merged = _merge(base)
    for block_start, block_end in block_intervals.get(day, []):
        merged = _subtract(merged, block_start, block_end)
    return merged


def _overlaps_any(start: datetime, end: datetime, busy: list[Interval]) -> bool:
    """Полуоткрытое пересечение [start, end) с любым занятым интервалом (busy отсортирован)."""
    for b_start, b_end in busy:
        if b_start >= end:
            break  # дальше только позже — пересечений быть не может
        if start < b_end and b_start < end:
            return True
    return False


def _index_exceptions(
    exceptions: Iterable[DayException],
) -> tuple[set[date], dict[date, list[TimeRange]], dict[date, list[TimeRange]]]:
    blocks_full: set[date] = set()
    block_intervals: dict[date, list[TimeRange]] = defaultdict(list)
    extra_intervals: dict[date, list[TimeRange]] = defaultdict(list)
    for exc in exceptions:
        parsed = [_parse_pair(p) for p in exc.interval]
        if exc.type == "block":
            if parsed:
                block_intervals[exc.date].extend(parsed)
            else:
                blocks_full.add(exc.date)
        elif exc.type == "extra":
            extra_intervals[exc.date].extend(parsed)
    return blocks_full, block_intervals, extra_intervals


def build_slots(
    *,
    duration_minutes: int,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    min_notice_minutes: int,
    max_horizon_days: int,
    daily_limit: int | None,
    is_active: bool,
    rules: dict[str, list[list[str]]],
    exceptions: Iterable[DayException],
    busy: list[Interval],
    booked_counts_by_date: dict[date, int],
    host_tz: str,
    invitee_tz: str,
    range_from: date,
    range_to: date,
    now_utc: datetime,
    granularity_minutes: int | None = None,
) -> list[Slot]:
    """Возвращает свободные слоты в диапазоне [range_from, range_to]. См. модульный docstring."""
    if not is_active:
        return []

    host_zone = ZoneInfo(host_tz)
    invitee_zone = ZoneInfo(invitee_tz)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=granularity_minutes or duration_minutes)
    earliest = now_utc + timedelta(minutes=min_notice_minutes)
    horizon_end = now_utc + timedelta(days=max_horizon_days)

    blocks_full, block_intervals, extra_intervals = _index_exceptions(exceptions)
    busy = sorted(busy)

    slots: list[Slot] = []
    day = range_from
    while day <= range_to:
        for window_start_t, window_end_t in _day_windows(
            day, rules, blocks_full, block_intervals, extra_intervals
        ):
            window_start_local = datetime.combine(day, window_start_t, tzinfo=host_zone)
            window_end_local = datetime.combine(day, window_end_t, tzinfo=host_zone)
            candidate_local = window_start_local
            while candidate_local + duration <= window_end_local:
                start_utc = candidate_local.astimezone(UTC)
                # Пропускаем несуществующее локальное время (DST spring-forward): если обратная
                # конвертация не совпадает по настенным часам — такого времени не было.
                if start_utc.astimezone(host_zone).replace(tzinfo=None) != candidate_local.replace(
                    tzinfo=None
                ):
                    candidate_local += step
                    continue

                end_utc = (candidate_local + duration).astimezone(UTC)
                slot_date = candidate_local.date()
                within_bounds = start_utc >= earliest and end_utc <= horizon_end
                under_limit = (
                    daily_limit is None
                    or booked_counts_by_date.get(slot_date, 0) < daily_limit
                )

                if within_bounds and under_limit:
                    occupied_start = start_utc - timedelta(minutes=buffer_before_minutes)
                    occupied_end = end_utc + timedelta(minutes=buffer_after_minutes)
                    if not _overlaps_any(occupied_start, occupied_end, busy):
                        slots.append(
                            Slot(
                                start_utc=start_utc,
                                end_utc=end_utc,
                                start_local=start_utc.astimezone(invitee_zone),
                            )
                        )
                candidate_local += step
        day += timedelta(days=1)

    slots.sort(key=lambda s: s.start_utc)
    return slots


# --- Слой БД ---


async def get_busy_intervals(
    db: AsyncSession, host_id: uuid.UUID, window_start_utc: datetime, window_end_utc: datetime
) -> list[Interval]:
    """Занятые интервалы хоста в окне (брони + их буферы).

    Шов для будущего среза календарей: сюда же будут добавляться busy-интервалы из
    подключённых внешних календарей (CalendarConnection).
    """
    rows = (
        await db.execute(
            select(
                Booking.start_utc,
                Booking.end_utc,
                EventType.buffer_before_minutes,
                EventType.buffer_after_minutes,
            )
            .join(EventType, Booking.event_type_id == EventType.id)
            .where(
                Booking.host_id == host_id,
                Booking.status.in_(ACTIVE_STATUSES),
                Booking.end_utc > window_start_utc,
                Booking.start_utc < window_end_utc,
            )
        )
    ).all()
    busy = [
        (start - timedelta(minutes=before), end + timedelta(minutes=after))
        for start, end, before, after in rows
    ]
    # TODO(срез календарей §4.6): добавить busy из CalendarConnection.
    busy.sort()
    return busy


async def _daily_counts(
    db: AsyncSession,
    event_type_id: uuid.UUID,
    host_zone: ZoneInfo,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> dict[date, int]:
    """Число активных броней этого типа по host-local датам (для daily_limit, ТЗ §4.3)."""
    starts = await db.scalars(
        select(Booking.start_utc).where(
            Booking.event_type_id == event_type_id,
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.start_utc >= window_start_utc,
            Booking.start_utc < window_end_utc,
        )
    )
    counts: dict[date, int] = defaultdict(int)
    for start in starts:
        counts[start.astimezone(host_zone).date()] += 1
    return counts


async def compute_available_slots(
    db: AsyncSession,
    event_type: EventType,
    *,
    range_from: date,
    range_to: date,
    invitee_tz: str,
    now: datetime | None = None,
) -> list[Slot]:
    """Подгружает расписание/занятость и считает слоты для типа встречи."""
    now_utc = now or datetime.now(UTC)
    user = await db.get(User, event_type.user_id)
    schedule = await get_default_schedule(db, event_type.user_id)
    host_tz = resolve_timezone(schedule, user) if user else "UTC"
    host_zone = ZoneInfo(host_tz)

    window_start_utc = datetime.combine(range_from, time.min, tzinfo=host_zone).astimezone(UTC)
    window_end_utc = datetime.combine(
        range_to + timedelta(days=1), time.min, tzinfo=host_zone
    ).astimezone(UTC)

    exception_rows = await db.scalars(
        select(AvailabilityException).where(
            AvailabilityException.schedule_id == schedule.id,
            AvailabilityException.date >= range_from,
            AvailabilityException.date <= range_to,
        )
    )
    exceptions = [
        DayException(date=e.date, type=e.type, interval=e.interval) for e in exception_rows
    ]
    busy = await get_busy_intervals(db, event_type.user_id, window_start_utc, window_end_utc)
    counts = await _daily_counts(
        db, event_type.id, host_zone, window_start_utc, window_end_utc
    )

    return build_slots(
        duration_minutes=event_type.duration_minutes,
        buffer_before_minutes=event_type.buffer_before_minutes,
        buffer_after_minutes=event_type.buffer_after_minutes,
        min_notice_minutes=event_type.min_notice_minutes,
        max_horizon_days=event_type.max_horizon_days,
        daily_limit=event_type.daily_limit,
        is_active=event_type.is_active,
        rules=schedule.rules,
        exceptions=exceptions,
        busy=busy,
        booked_counts_by_date=counts,
        host_tz=host_tz,
        invitee_tz=invitee_tz,
        range_from=range_from,
        range_to=range_to,
        now_utc=now_utc,
    )
