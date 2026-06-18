# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала только метаданные пакета — кешируется слой с зависимостями.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Исходники миграций и конфиг Alembic.
COPY alembic.ini ./
COPY migrations ./migrations

# Непривилегированный пользователь.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# По умолчанию — API. Воркер/бит переопределяют команду в docker-compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
