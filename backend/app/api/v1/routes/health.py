"""Health- и readiness-проверки."""

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness-проба")
async def health() -> dict[str, str]:
    """Простая проверка, что процесс жив."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness-проба (включая БД)")
async def ready(db: DbSession, response: Response) -> dict[str, str]:
    """Проверяет доступность зависимостей (БД). Используется оркестратором.

    Возвращает 503, если БД недоступна, чтобы трафик не направлялся на под.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}
