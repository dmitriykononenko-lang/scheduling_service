import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


async def test_register_returns_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "supersecret1", "name": "Иван Петров"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "supersecret1", "name": "Тест"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_and_me_flow(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "Мария"},
    )

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    data = me.json()
    assert data["email"] == email
    assert data["slug"]  # публичная ссылка сгенерирована


async def test_login_wrong_password_rejected(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "Пётр"},
    )
    bad = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert bad.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
