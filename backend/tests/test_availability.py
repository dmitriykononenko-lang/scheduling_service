import uuid

from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"host-{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "Хост"},
    )
    return resp.json()["access_token"]


async def test_default_schedule_created_on_register(client: AsyncClient) -> None:
    token = await _register(client)
    resp = await client.get(
        "/api/v1/availability/schedule", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_default"] is True
    assert body["rules"]["mon"] == [["10:00", "18:00"]]
    assert "sat" not in body["rules"]  # выходные пустые


async def test_patch_rules(client: AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/api/v1/availability/schedule",
        headers=headers,
        json={"rules": {"mon": [["09:00", "13:00"], ["14:00", "18:00"]]}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rules"]["mon"] == [["09:00", "13:00"], ["14:00", "18:00"]]


async def test_invalid_rules_rejected(client: AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    # start >= end
    bad1 = await client.patch(
        "/api/v1/availability/schedule",
        headers=headers,
        json={"rules": {"mon": [["18:00", "10:00"]]}},
    )
    assert bad1.status_code == 422
    # пересекающиеся интервалы
    bad2 = await client.patch(
        "/api/v1/availability/schedule",
        headers=headers,
        json={"rules": {"mon": [["10:00", "13:00"], ["12:00", "14:00"]]}},
    )
    assert bad2.status_code == 422
    # некорректный день недели
    bad3 = await client.patch(
        "/api/v1/availability/schedule",
        headers=headers,
        json={"rules": {"xyz": [["10:00", "11:00"]]}},
    )
    assert bad3.status_code == 422


async def test_exceptions_crud(client: AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/availability/exceptions",
        headers=headers,
        json={"date": "2026-07-06", "type": "block"},
    )
    assert created.status_code == 201, created.text
    exc_id = created.json()["id"]

    listed = await client.get("/api/v1/availability/exceptions", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client.delete(f"/api/v1/availability/exceptions/{exc_id}", headers=headers)
    assert deleted.status_code == 204


async def test_extra_exception_requires_interval(client: AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/availability/exceptions",
        headers=headers,
        json={"date": "2026-07-11", "type": "extra"},  # extra без interval
    )
    assert resp.status_code == 422


async def test_exception_ownership_enforced(client: AsyncClient) -> None:
    token_a = await _register(client)
    token_b = await _register(client)
    created = await client.post(
        "/api/v1/availability/exceptions",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"date": "2026-07-06", "type": "block"},
    )
    exc_id = created.json()["id"]
    # Пользователь B не должен видеть/менять исключение пользователя A.
    resp = await client.delete(
        f"/api/v1/availability/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
