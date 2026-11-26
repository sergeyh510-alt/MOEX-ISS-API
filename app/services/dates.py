"""Конвертация date_key (int YYYYMMDD) <-> datetime.date с валидацией."""

from datetime import date

MIN_DATE_KEY = 19000101
MAX_DATE_KEY = 99991231


def date_key_to_date(date_key: int | None) -> date | None:
    """Преобразовать date_key (int YYYYMMDD) в datetime.date.

    Пустое значение (None) даёт None. Некорректный date_key (не 8 цифр, вне
    диапазона или несуществующая дата, например февраль 30) даёт ValueError.
    """

    if date_key is None:
        return None
    if not isinstance(date_key, int):
        raise ValueError(f"date_key должен быть целым числом, получено {type(date_key)}")
    if date_key < MIN_DATE_KEY or date_key > MAX_DATE_KEY:
        raise ValueError(f"date_key вне диапазона {MIN_DATE_KEY}..{MAX_DATE_KEY}: {date_key}")
    digits = f"{date_key:08d}"
    try:
        return date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError as exc:
        raise ValueError(f"некорректная дата для date_key={date_key}: {exc}") from exc


def date_to_date_key(value: date | None) -> int | None:
    """Преобразовать datetime.date в date_key (int YYYYMMDD)."""

    if value is None:
        return None
    return value.year * 10000 + value.month * 100 + value.day


def parse_iso_date(value: str | None) -> date | None:
    """Разобрать дату в формате YYYY-MM-DD, ошибка для неверного формата."""

    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"некорректная дата {value!r}, ожидается YYYY-MM-DD") from exc

