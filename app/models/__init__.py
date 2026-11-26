"""SQLAlchemy-модели мини-DWH (read-only).

Импорт модулей по слоям регистрирует все таблицы в Base.metadata.
"""

from app.models.audit import DqCheck, DqRun
from app.models.base import Base
from app.models.core import DimDate, DimSecurity, FactDailyIndex, FactDailyPrice
from app.models.mart import DailyMover, IndexCompare, StockReturn
from app.models.meta import LoadRun, Source

__all__ = [
    "Base",
    "DailyMover",
    "DimDate",
    "DimSecurity",
    "DqCheck",
    "DqRun",
    "FactDailyIndex",
    "FactDailyPrice",
    "IndexCompare",
    "LoadRun",
    "Source",
    "StockReturn",
]
