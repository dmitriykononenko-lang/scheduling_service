import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import QuestionFieldType
from app.models.event_type import Question


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


async def test_public_detail_exposes_questions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Страница записи (ТЗ §4.4) должна получать анкету: публичный детальный эндпоинт
    отдаёт вопросы, отсортированные по position."""
    token, slug = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/event-types",
        headers=headers,
        json={"title": "Консультация", "slug": "consult", "duration_minutes": 30},
    )
    event_id = uuid.UUID(created.json()["id"])

    # Вопросы добавляем напрямую (CRUD вопросов хостом — отдельный срез). Порядок вставки
    # обратный позиции — проверяем сортировку по Question.position.
    db_session.add_all(
        [
            Question(
                event_type_id=event_id,
                label="Город",
                field_type=QuestionFieldType.select,
                required=False,
                options=["Москва", "СПб"],
                position=2,
            ),
            Question(
                event_type_id=event_id,
                label="Телефон",
                field_type=QuestionFieldType.text,
                required=True,
                position=1,
            ),
        ]
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/public/{slug}/event-types/consult")
    assert resp.status_code == 200, resp.text
    questions = resp.json()["questions"]
    assert [q["label"] for q in questions] == ["Телефон", "Город"]  # порядок по position
    phone, city = questions
    assert phone["field_type"] == "text"
    assert phone["required"] is True
    assert city["field_type"] == "select"
    assert city["options"] == ["Москва", "СПб"]
