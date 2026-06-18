"""Безопасность: хеширование паролей (argon2) и выпуск/проверка JWT.

ТЗ §9: хеширование паролей argon2/bcrypt, JWT-сессии.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, Exception):  # noqa: BLE001 — любая ошибка проверки = неуспех
        return False


def needs_rehash(password_hash: str) -> bool:
    """Сообщает, устарели ли параметры хеша (для прозрачного апгрейда при логине)."""
    return _password_hasher.check_needs_rehash(password_hash)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT. Бросает jwt.PyJWTError при ошибке."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def generate_api_key() -> tuple[str, str]:
    """Возвращает (plaintext_key, sha256_hash). В БД хранится только хеш (ТЗ §9)."""
    import hashlib

    raw = f"sk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash
