# Scheduling Service

SaaS-сервис планирования встреч и онлайн-записи для русскоязычного рынка (фрилансеры,
IT-специалисты, консультанты). Аналог Calendly с акцентом на **публичный API + webhooks**,
корректные **часовые пояса** и **приём предоплаты в рублях**.

> Каркас монорепозитория (фаза «фундамент»). Реализация фич MVP ведётся поверх него
> согласно ТЗ. См. [`docs/architecture.md`](docs/architecture.md) и
> [`docs/roadmap.md`](docs/roadmap.md).

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Очереди | Celery + Redis (worker и beat) |
| БД | PostgreSQL 16 |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS |
| Инфра | Docker / docker-compose, GitHub Actions CI |

## Структура

```
.
├── backend/            # FastAPI-приложение
│   ├── app/
│   │   ├── api/        # роуты (v1: auth, event-types, public, health)
│   │   ├── core/       # config, database, security, logging
│   │   ├── models/     # SQLAlchemy-модели (см. §7 ТЗ)
│   │   ├── schemas/    # Pydantic-схемы (DTO)
│   │   ├── services/   # бизнес-логика
│   │   └── workers/    # Celery: задачи и расписание
│   ├── migrations/     # Alembic
│   └── tests/          # pytest
├── frontend/           # Next.js-приложение
│   ├── app/            # страницы (лендинг, публичная страница записи /[slug])
│   └── lib/            # API-клиент
├── docs/               # архитектура и роадмап
├── docker-compose.yml  # локальный стек целиком
└── .github/workflows/  # CI
```

## Быстрый старт (Docker)

```bash
cp .env.example .env
# отредактируйте SECRET_KEY в .env
docker compose up --build
```

- API: http://localhost:8000 — Swagger UI на `/docs`, ReDoc на `/redoc`
- Frontend: http://localhost:3000
- Миграции применяются автоматически при старте контейнера `api`.

## Локальная разработка без Docker

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# нужна работающая PostgreSQL; задайте DATABASE_URL при необходимости
export DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/scheduling
alembic upgrade head
uvicorn app.main:app --reload
```

Тесты (нужна тестовая БД, по умолчанию `scheduling_test`):

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/scheduling_test
ruff check .
pytest
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev      # http://localhost:3000
npm run lint && npm run typecheck && npm run build
```

## Что уже есть в каркасе

- Регистрация / вход (email + пароль), JWT, `GET /auth/me`; argon2-хеширование паролей.
- Полная модель данных из §7 ТЗ (12 сущностей) + Alembic-миграция.
- **Запрет двойных броней на уровне БД**: EXCLUDE-ограничение (btree_gist) на пересечение
  активных броней одного хоста — закрывает КП §4.2 и требование §7.
- CRUD типов встреч и публичные эндпоинты страницы записи (видимость public/unlisted).
- Каркас Celery (worker + beat): задачи напоминаний, синхронизации календарей, доставки webhooks.
- Лендинг и публичная страница записи `/{slug}`, тянущая данные из API.
- CI: lint + миграции + тесты (backend), lint + typecheck + build (frontend).

Подробный статус по фазам — в [`docs/roadmap.md`](docs/roadmap.md).
