import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event_type import EventType, Question
from app.models.user import User


async def _setup(client: AsyncClient, *, requires_prepay: bool = False) -> dict:
    """Регистрирует хоста и создаёт активный тип встречи. Дефолтное расписание уже есть."""
    email = f"host-{uuid.uuid4().hex[:10]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "Хост"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    slug = me.json()["slug"]
    et = await client.post(
        "/api/v1/event-types",
        headers=headers,
        json={
            "title": "Консультация",
            "slug": "consult",
            "duration_minutes": 30,
            "requires_prepay": requires_prepay,
        },
    )
    return {
        "token": token,
        "headers": headers,
        "slug": slug,
        "event_slug": et.json()["slug"],
        "event_id": et.json()["id"],
    }


async def _slots(client: AsyncClient, slug: str, event_slug: str) -> list[str]:
    resp = await client.get(f"/api/v1/public/{slug}/event-types/{event_slug}/slots")
    assert resp.status_code == 200, resp.text
    return [s["start_utc"] for s in resp.json()["slots"]]


async def _book(client: AsyncClient, slug: str, event_slug: str, start_utc: str, **extra):
    payload = {"start_utc": start_utc, "invitee_name": "Гость", "invitee_contact": "g@example.com"}
    payload.update(extra)
    return await client.post(
        f"/api/v1/public/{slug}/event-types/{event_slug}/bookings", json=payload
    )


async def test_booking_happy_path_free(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    assert slots, "ожидаем непустую выдачу слотов по дефолтному расписанию"

    resp = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["booking"]["status"] == "confirmed"
    assert body["management_token"]
    assert body["management_token"] in body["manage_url"]


async def test_prepay_booking_is_pending_payment(client: AsyncClient) -> None:
    ctx = await _setup(client, requires_prepay=True)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    resp = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    assert resp.status_code == 201, resp.text
    assert resp.json()["booking"]["status"] == "pending_payment"


async def test_double_booking_same_slot_conflicts(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    first = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    assert first.status_code == 201
    second = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    assert second.status_code == 409


async def test_booked_slot_disappears_from_listing(client: AsyncClient) -> None:
    ctx = await _setup(client)
    before = await _slots(client, ctx["slug"], ctx["event_slug"])
    await _book(client, ctx["slug"], ctx["event_slug"], before[0])
    after = await _slots(client, ctx["slug"], ctx["event_slug"])
    assert before[0] not in after
    assert before[1] in after  # смежный остаётся


async def test_required_question_enforced(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(client)
    # Добавляем обязательный вопрос напрямую (API вопросов — отдельный срез).
    question = Question(
        event_type_id=uuid.UUID(ctx["event_id"]), label="Телефон", required=True
    )
    db_session.add(question)
    await db_session.commit()

    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    resp = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])  # без answers
    assert resp.status_code == 422


async def test_host_can_list_and_cancel_freeing_slot(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    booked = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    booking_id = booked.json()["booking"]["id"]

    listed = await client.get("/api/v1/bookings", headers=ctx["headers"])
    assert listed.status_code == 200
    assert any(b["id"] == booking_id for b in listed.json())

    canceled = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=ctx["headers"], json={"reason": "тест"}
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"

    after = await _slots(client, ctx["slug"], ctx["event_slug"])
    assert slots[0] in after  # слот вернулся в выдачу


async def test_guest_get_booking_includes_context(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    booked = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    token = booked.json()["management_token"]

    resp = await client.get(f"/api/v1/public/manage/{token}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Контекст для гостевой страницы управления: показать встречу и подгрузить
    # слоты для переноса (слот-эндпоинт ключуется по слугам).
    assert body["host_slug"] == ctx["slug"]
    assert body["event_slug"] == ctx["event_slug"]
    assert body["event_title"] == "Консультация"
    assert body["event_duration_minutes"] == 30
    assert body["host_name"] == "Хост"
    assert body["host_timezone"]
    assert body["requires_prepay"] is False
    assert body["status"] == "confirmed"


async def test_guest_cancel_by_token(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    booked = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    token = booked.json()["management_token"]

    unknown = await client.post("/api/v1/public/manage/nope-nope/cancel", json={})
    assert unknown.status_code == 404

    canceled = await client.post(f"/api/v1/public/manage/{token}/cancel", json={})
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"


async def test_guest_reschedule_is_atomic(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    booked = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    old_id = booked.json()["booking"]["id"]
    token = booked.json()["management_token"]

    resp = await client.post(
        f"/api/v1/public/manage/{token}/reschedule", json={"start_utc": slots[1]}
    )
    assert resp.status_code == 200, resp.text
    new_booking = resp.json()["booking"]
    assert new_booking["status"] == "confirmed"
    assert new_booking["rescheduled_from_id"] == old_id
    assert new_booking["start_utc"].startswith(slots[1][:16])

    # Старый слот освободился, новый — занят.
    after = await _slots(client, ctx["slug"], ctx["event_slug"])
    assert slots[0] in after
    assert slots[1] not in after

    # Старая бронь помечена как rescheduled.
    listed = await client.get("/api/v1/bookings", headers=ctx["headers"])
    statuses = {b["id"]: b["status"] for b in listed.json()}
    assert statuses[old_id] == "rescheduled"


async def test_reschedule_onto_taken_slot_keeps_original(client: AsyncClient) -> None:
    ctx = await _setup(client)
    slots = await _slots(client, ctx["slug"], ctx["event_slug"])
    first = await _book(client, ctx["slug"], ctx["event_slug"], slots[0])
    token = first.json()["management_token"]
    await _book(client, ctx["slug"], ctx["event_slug"], slots[1])  # занимаем второй слот

    resp = await client.post(
        f"/api/v1/public/manage/{token}/reschedule", json={"start_utc": slots[1]}
    )
    assert resp.status_code == 409

    # Исходная бронь не изменилась.
    current = await client.get(f"/api/v1/public/manage/{token}")
    assert current.status_code == 200
    assert current.json()["status"] == "confirmed"
    assert current.json()["start_utc"].startswith(slots[0][:16])


async def test_db_constraint_rejects_overlapping_bookings(db_session: AsyncSession) -> None:
    """Прямая проверка, что EXCLUDE-ограничение присутствует и отвергает наложение."""
    user = User(email=f"u-{uuid.uuid4().hex[:8]}@e.com", name="U", slug=f"u-{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    event_type = EventType(user_id=user.id, title="T", slug="t", duration_minutes=30)
    db_session.add(event_type)
    await db_session.flush()

    first = Booking(
        event_type_id=event_type.id,
        host_id=user.id,
        invitee_name="A",
        invitee_contact="a",
        start_utc=datetime(2030, 1, 1, 10, 0, tzinfo=UTC),
        end_utc=datetime(2030, 1, 1, 10, 30, tzinfo=UTC),
        status=BookingStatus.confirmed,
    )
    db_session.add(first)
    await db_session.commit()

    overlapping = Booking(
        event_type_id=event_type.id,
        host_id=user.id,
        invitee_name="B",
        invitee_contact="b",
        start_utc=datetime(2030, 1, 1, 10, 15, tzinfo=UTC),
        end_utc=datetime(2030, 1, 1, 10, 45, tzinfo=UTC),
        status=BookingStatus.confirmed,
    )
    db_session.add(overlapping)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
