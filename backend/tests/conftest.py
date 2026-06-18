"""Фикстуры тестов: изолированная тестовая БД и HTTP-клиент поверх ASGI."""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.constraints import ADD_OVERLAP_CONSTRAINT_SQL, CREATE_BTREE_GIST_SQL
from app.main import app
from app.models import Base

# Тестовая БД отдельная от рабочей. В CI поднимается сервисным контейнером Postgres.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5432/scheduling_test",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Создаёт схему в тестовой БД на время теста и выдаёт сессию; затем удаляет схему.

    `create_all` не создаёт EXCLUDE-ограничение из миграции, поэтому добавляем его вручную из
    общего DDL-константа (app.db.constraints) — иначе тесты на двойную бронь были бы ложно
    зелёными.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        # gen_random_uuid() доступна в ядре PostgreSQL 13+.
        await conn.execute(text(CREATE_BTREE_GIST_SQL))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(ADD_OVERLAP_CONSTRAINT_SQL))

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент с подменённой зависимостью БД на тестовую сессию."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
