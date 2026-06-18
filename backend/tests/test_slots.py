"""Юнит-тесты алгоритма расчёта слотов (чистая build_slots, без БД)."""

from datetime import UTC, date, datetime, timedelta

from app.schemas.availability import WEEKDAYS
from app.services.slots import DayException, build_slots

MONDAY = date(2026, 7, 6)  # будний день для базовых проверок


def _rules_all(intervals: list[list[str]]) -> dict[str, list[list[str]]]:
    return dict.fromkeys(WEEKDAYS, intervals)


def run(**overrides) -> list:
    params = {
        "duration_minutes": 30,
        "buffer_before_minutes": 0,
        "buffer_after_minutes": 0,
        "min_notice_minutes": 0,
        "max_horizon_days": 3650,
        "daily_limit": None,
        "is_active": True,
        "rules": {},
        "exceptions": [],
        "busy": [],
        "booked_counts_by_date": {},
        "host_tz": "Europe/Moscow",
        "invitee_tz": "Europe/Moscow",
        "range_from": MONDAY,
        "range_to": MONDAY,
        "now_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    params.update(overrides)
    return build_slots(**params)


def test_basic_grid_moscow() -> None:
    slots = run(rules=_rules_all([["10:00", "12:00"]]))
    starts = [s.start_utc for s in slots]
    # Москва UTC+3, без перехода на летнее время.
    assert starts == [
        datetime(2026, 7, 6, 7, 0, tzinfo=UTC),
        datetime(2026, 7, 6, 7, 30, tzinfo=UTC),
        datetime(2026, 7, 6, 8, 0, tzinfo=UTC),
        datetime(2026, 7, 6, 8, 30, tzinfo=UTC),
    ]
    assert slots[-1].end_utc == datetime(2026, 7, 6, 9, 0, tzinfo=UTC)
    assert [s.start_local.hour for s in slots] == [10, 10, 11, 11]


def test_back_to_back_no_slot_exceeds_window() -> None:
    slots = run(rules=_rules_all([["10:00", "11:15"]]), duration_minutes=30)
    # 10:00–10:30, 10:30–11:00; 11:00–11:30 вышло бы за 11:15 → не создаётся.
    assert len(slots) == 2


def test_min_notice_boundary_inclusive() -> None:
    # earliest == 07:30 UTC: слот 07:00 отброшен, 07:30 включён (граница по >=).
    slots = run(
        rules=_rules_all([["10:00", "12:00"]]),
        now_utc=datetime(2026, 7, 6, 7, 30, tzinfo=UTC),
    )
    assert [s.start_utc for s in slots][0] == datetime(2026, 7, 6, 7, 30, tzinfo=UTC)
    assert len(slots) == 3


def test_max_horizon_clips_future_days() -> None:
    slots = run(
        rules=_rules_all([["10:00", "12:00"]]),
        range_from=MONDAY,
        range_to=MONDAY + timedelta(days=4),
        now_utc=datetime(2026, 7, 6, 0, 0, tzinfo=UTC),
        max_horizon_days=1,
    )
    # horizon = now + 1 день → только слоты 6 июля.
    assert slots
    assert all(s.start_utc.date() == date(2026, 7, 6) for s in slots)


def test_daily_limit_at_capacity_yields_nothing() -> None:
    rules = _rules_all([["10:00", "12:00"]])
    at_limit = run(rules=rules, daily_limit=2, booked_counts_by_date={MONDAY: 2})
    below = run(rules=rules, daily_limit=2, booked_counts_by_date={MONDAY: 1})
    assert at_limit == []
    assert below


def test_full_day_block_empties_day() -> None:
    slots = run(
        rules=_rules_all([["10:00", "12:00"]]),
        exceptions=[DayException(date=MONDAY, type="block", interval=[])],
    )
    assert slots == []


def test_partial_block_subtracts_interval() -> None:
    slots = run(
        rules=_rules_all([["10:00", "12:00"]]),
        exceptions=[DayException(date=MONDAY, type="block", interval=[["10:30", "11:30"]])],
    )
    # Остаются 10:00–10:30 и 11:30–12:00.
    assert [s.start_local.strftime("%H:%M") for s in slots] == ["10:00", "11:30"]


def test_extra_adds_hours_on_empty_day() -> None:
    slots = run(
        rules={},  # по правилам день пустой
        exceptions=[DayException(date=MONDAY, type="extra", interval=[["10:00", "11:00"]])],
    )
    assert [s.start_local.strftime("%H:%M") for s in slots] == ["10:00", "10:30"]


def test_busy_removes_overlapping_keeps_adjacent() -> None:
    # Занят 10:30–11:00 МСК = 07:30–08:00 UTC.
    busy = [(datetime(2026, 7, 6, 7, 30, tzinfo=UTC), datetime(2026, 7, 6, 8, 0, tzinfo=UTC))]
    slots = run(rules=_rules_all([["10:00", "12:00"]]), busy=busy)
    labels = [s.start_local.strftime("%H:%M") for s in slots]
    assert "10:30" not in labels  # пересекается
    assert labels == ["10:00", "11:00", "11:30"]  # смежные сохранены (полуинтервал)


def test_buffers_expand_candidate_footprint() -> None:
    # Существующая встреча 11:00–11:30 с буферами 15/15 → занятый интервал 10:45–11:45 МСК
    # = 07:45–08:45 UTC. Кандидаты с буфером 15/15 вокруг неё отсекаются.
    busy = [(datetime(2026, 7, 6, 7, 45, tzinfo=UTC), datetime(2026, 7, 6, 8, 45, tzinfo=UTC))]
    slots = run(
        rules=_rules_all([["10:00", "12:00"]]),
        buffer_before_minutes=15,
        buffer_after_minutes=15,
        busy=busy,
    )
    assert [s.start_local.strftime("%H:%M") for s in slots] == ["10:00"]


def test_invitee_tz_only_affects_display() -> None:
    rules = _rules_all([["10:00", "12:00"]])
    msk = run(rules=rules, invitee_tz="Europe/Moscow")
    nyc = run(rules=rules, invitee_tz="America/New_York")
    assert [s.start_utc for s in msk] == [s.start_utc for s in nyc]
    assert msk[0].start_local.hour != nyc[0].start_local.hour


def test_inactive_event_type_returns_empty() -> None:
    assert run(rules=_rules_all([["10:00", "12:00"]]), is_active=False) == []


def test_empty_schedule_returns_empty() -> None:
    assert run(rules={}) == []


def test_dst_spring_forward_skips_nonexistent_hour() -> None:
    # Берлин 2026-03-29: 02:00 → 03:00. Окно 01:00–04:00, слоты по 60 мин.
    spring = date(2026, 3, 29)
    slots = run(
        rules=_rules_all([["01:00", "04:00"]]),
        duration_minutes=60,
        host_tz="Europe/Berlin",
        invitee_tz="Europe/Berlin",
        range_from=spring,
        range_to=spring,
    )
    locals_ = [s.start_local.strftime("%H:%M") for s in slots]
    assert locals_ == ["01:00", "03:00"]  # 02:00 не существует — пропущен
    assert slots[0].start_utc == datetime(2026, 3, 29, 0, 0, tzinfo=UTC)  # 01:00 CET
    assert slots[1].start_utc == datetime(2026, 3, 29, 1, 0, tzinfo=UTC)  # 03:00 CEST


def test_dst_fall_back_uses_first_occurrence() -> None:
    # Берлин 2026-10-25: 03:00 → 02:00. Окно 01:00–04:00, слоты по 60 мин.
    fall = date(2026, 10, 25)
    slots = run(
        rules=_rules_all([["01:00", "04:00"]]),
        duration_minutes=60,
        host_tz="Europe/Berlin",
        invitee_tz="Europe/Berlin",
        range_from=fall,
        range_to=fall,
    )
    locals_ = [s.start_local.strftime("%H:%M") for s in slots]
    # Каждое настенное время — один раз (fold=0): повторный «02:00» не дублируется.
    assert locals_ == ["01:00", "02:00", "03:00"]
    starts = [s.start_utc for s in slots]
    assert len(set(starts)) == 3  # UTC-инстанты различны
