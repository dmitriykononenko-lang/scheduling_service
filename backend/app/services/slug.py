"""Генерация и нормализация slug для публичных ссылок (ТЗ §4.1)."""

import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

# Простая транслитерация кириллицы для slug вида domain.ru/ivan-petrov.
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = "".join(_TRANSLIT.get(ch, ch) for ch in value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:48] or f"user-{secrets.token_hex(3)}"


async def generate_unique_user_slug(db: AsyncSession, base: str) -> str:
    """Подбирает свободный slug, добавляя суффикс при коллизии."""
    candidate = slugify(base)
    suffix = 0
    while True:
        probe = candidate if suffix == 0 else f"{candidate}-{suffix}"
        exists = await db.scalar(
            select(func.count()).select_from(User).where(User.slug == probe)
        )
        if not exists:
            return probe
        suffix += 1
        if suffix > 50:  # на всякий случай — гарантированно уникальный хвост
            return f"{candidate}-{secrets.token_hex(3)}"
