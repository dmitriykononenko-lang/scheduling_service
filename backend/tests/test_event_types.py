import uuid

from httpx import AsyncClient


async def _register(client: AsyncClient) -> tuple[str, str]:
    """Регистрирует пользователя, возвращает (token, slug)."""
    email = f"host-{uuid.uuid4().hex[:10]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "Хост Тестов"},
    )
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["slug"]


async def test_create_and_list_event_type(client: AsyncClient) -> None:
    token, _ = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/event-types",
        headers=headers,
        json={"title": "Консультация 30 мин", "slug": "consult-30", "duration_minutes": 30},
    )
    assert created.status_code == 201, created.text
    assert created.json()["slug"] == "consult-30"

    listed = await client.get("/api/v1/event-types", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_unlisted_event_type_hidden_from_public_profile(client: AsyncClient) -> None:
    token, slug = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Публичный тип
    await client.post(
        "/api/v1/event-types",
        headers=headers,
        json={"title": "Публичная", "slug": "public-call", "visibility": "public"},
    )
    # Скрытый тип (по прямой ссылке)
    await client.post(
        "/api/v1/event-types",
        headers=headers,
        json={"title": "Скрытая", "slug": "secret-call", "visibility": "unlisted"},
    )

    public_list = await client.get(f"/api/v1/public/{slug}/event-types")
    assert public_list.status_code == 200
    slugs = [item["slug"] for item in public_list.json()]
    assert "public-call" in slugs
    assert "secret-call" not in slugs  # ТЗ §4.3 КП: скрытый не виден в общем профиле

    # …но доступен по прямой ссылке
    direct = await client.get(f"/api/v1/public/{slug}/event-types/secret-call")
    assert direct.status_code == 200
    assert direct.json()["slug"] == "secret-call"


async def test_create_event_type_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/event-types",
        json={"title": "No auth", "slug": "no-auth"},
    )
    assert resp.status_code == 401
