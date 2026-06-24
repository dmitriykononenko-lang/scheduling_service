# Backend — Созвон

FastAPI + SQLAlchemy 2.0 (async) + Alembic + Celery.

## Команды

```bash
pip install -e ".[dev]"        # установка с dev-зависимостями

ruff check .                   # линт
ruff check --fix .             # автоисправления
pytest                         # тесты (нужна TEST_DATABASE_URL)

alembic upgrade head           # применить миграции
alembic revision --autogenerate -m "описание"   # новая миграция из изменений моделей
alembic check                  # проверить, что модели == миграции

uvicorn app.main:app --reload  # dev-сервер

# Фоновые задачи:
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

## Переменные окружения

Конфиг читается из окружения / `.env` (см. `app/core/config.py`). Ключевые:

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `ENVIRONMENT` | local/test/staging/production | `local` |
| `SECRET_KEY` | подпись JWT (≥32 байт в проде) | dev-заглушка |
| `DATABASE_URL` | async DSN PostgreSQL | localhost/scheduling |
| `REDIS_URL` | брокер Celery | localhost:6379/0 |
| `CORS_ORIGINS` | список origin через запятую | localhost:3000 |
| `TEST_DATABASE_URL` | БД для pytest | localhost/scheduling_test |

## Структура `app/`

- `core/` — конфигурация, async-движок БД, безопасность (argon2 + JWT), логирование.
- `models/` — ORM-модели (§7 ТЗ). Все импортируются в `models/__init__.py`.
- `schemas/` — Pydantic-DTO запросов/ответов.
- `api/v1/routes/` — эндпоинты; собираются в `api/v1/router.py`.
- `services/` — бизнес-логика (аутентификация, slug-и).
- `workers/` — Celery-приложение, задачи и расписание (beat).

## Заметки по схеме

- Первичные ключи — UUID (`gen_random_uuid()`), время — `TIMESTAMPTZ` (хранение в UTC, §5 ТЗ).
- Перечисления хранятся как VARCHAR + CHECK (`native_enum=False`) — проще эволюционировать.
- Брони защищены от пересечения EXCLUDE-ограничением `excl_bookings_host_no_overlap`
  (расширение `btree_gist`, полуинтервал `[)`, только для активных статусов).
