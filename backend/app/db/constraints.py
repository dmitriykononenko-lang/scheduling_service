"""Единый источник DDL для EXCLUDE-ограничения на пересечение броней.

Используется и Alembic-миграцией, и тестовой фикстурой (`Base.metadata.create_all` не
создаёт это ограничение), чтобы схема в тестах совпадала с продовой — без дублирования SQL.

Инвариант (ТЗ §4.2 КП, §7): у одного хоста не может быть двух пересекающихся активных встреч.
Активные статусы — `confirmed` и `pending_payment`. Статусы `canceled` и `rescheduled`
освобождают слот (поэтому в набор не входят — это важно для атомарного переноса, §4.5).
Полуинтервал `[)`: смежные встречи (конец == начало) пересечением не считаются.
"""

OVERLAP_CONSTRAINT_NAME = "excl_bookings_host_no_overlap"

# Статусы, при которых бронь занимает слот.
ACTIVE_BOOKING_STATUSES: tuple[str, ...] = ("confirmed", "pending_payment")

CREATE_BTREE_GIST_SQL = "CREATE EXTENSION IF NOT EXISTS btree_gist"

_STATUS_LIST = ", ".join(f"'{s}'" for s in ACTIVE_BOOKING_STATUSES)

ADD_OVERLAP_CONSTRAINT_SQL = f"""
ALTER TABLE bookings ADD CONSTRAINT {OVERLAP_CONSTRAINT_NAME}
EXCLUDE USING gist (
    host_id WITH =,
    tstzrange(start_utc, end_utc, '[)') WITH &&
)
WHERE (status IN ({_STATUS_LIST}))
""".strip()

DROP_OVERLAP_CONSTRAINT_SQL = (
    f"ALTER TABLE bookings DROP CONSTRAINT IF EXISTS {OVERLAP_CONSTRAINT_NAME}"
)
