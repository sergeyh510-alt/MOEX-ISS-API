"""Чистая математика доходности: период, среднее, волатильность, просадка.

Функции работают со списками чисел и не зависят от БД, чтобы их можно было
покрыть юнит-тестами. Проценты округляются до 4 знаков, цены не округляются.
"""

from statistics import mean, stdev

PCT_DIGITS = 4


def round_pct(value: float | None) -> float | None:
    """Округлить процент до 4 знаков (None остаётся None)."""

    if value is None:
        return None
    return round(value, PCT_DIGITS)


def period_return_pct(first_close: float | None, last_close: float | None) -> float | None:
    """Доходность за период: (last/first - 1) * 100."""

    if first_close is None or last_close is None or first_close == 0:
        return None
    return round_pct((last_close / first_close - 1.0) * 100.0)


def average(values: list[float]) -> float | None:
    """Среднее значение; None для пустого списка."""

    if not values:
        return None
    return mean(values)


def average_return_pct(values: list[float | None]) -> float | None:
    """Среднее дневной доходности; None-значения пропускаются."""

    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round_pct(mean(clean))


def sample_volatility_pct(values: list[float | None]) -> float | None:
    """Выборочное стандартное отклонение (stddev_samp) доходности, в процентах.

    None для менее чем двух значений (выборочная дисперсия требует n >= 2).
    """

    clean = [value for value in values if value is not None]
    if len(clean) < 2:
        return None
    return round_pct(stdev(clean))


def max_drawdown_pct(closes: list[float]) -> float | None:
    """Максимальная просадка от пика к минимуму по ряду close, в процентах.

    Ряд подаётся в порядке возрастания даты. Проходим по ряду, помним
    достигнутый пик и считаем максимальное падение от пика. Результат
    положительный: 12.5 значит падение на 12.5 процента. None для пустого ряда.
    """

    if not closes:
        return None
    peak = closes[0]
    worst = 0.0
    for close in closes:
        if close > peak:
            peak = close
        if peak > 0:
            drawdown = (peak - close) / peak * 100.0
            if drawdown > worst:
                worst = drawdown
    return round_pct(worst)


def min_max_index(values: list[float]) -> tuple[int, int] | None:
    """Индексы минимума и максимума ряда; None для пустого ряда."""

    if not values:
        return None
    min_index = min(range(len(values)), key=lambda index: values[index])
    max_index = max(range(len(values)), key=lambda index: values[index])
    return min_index, max_index
