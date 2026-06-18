"""Вспомогательные типы колонок для моделей."""

import enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=enum.Enum)


def enum_column(py_enum: type[E], length: int = 32) -> SAEnum:
    """Колонка-перечисление, хранимая как VARCHAR + CHECK (native_enum=False).

    Так проще эволюционировать схему в Alembic, чем нативные типы PostgreSQL ENUM,
    и хранится строковое значение (`.value`), а не имя члена.
    """
    return SAEnum(
        py_enum,
        native_enum=False,
        length=length,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )
