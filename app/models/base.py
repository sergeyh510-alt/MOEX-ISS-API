"""Базовый класс моделей SQLAlchemy 2.0.

Модели строго повторяют схему мини-DWH (авторитетный источник это слепок
``db/seed/01_seed.sql``). Все таблицы только для чтения.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Общая база для всех ORM-моделей проекта."""

