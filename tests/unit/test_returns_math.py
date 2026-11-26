"""Юнит-тесты чистой математики доходности (этап 3)."""

import pytest

from app.services import returns as math


def test_period_return_pct() -> None:
    """Доходность за период: (last/first - 1) * 100.

    100 -> 110 даёт 10 процентов; 100 -> 90 даёт -10 процентов.
    """

    assert math.period_return_pct(100.0, 110.0) == 10.0
    assert math.period_return_pct(100.0, 90.0) == -10.0
    assert math.period_return_pct(200.0, 250.0) == 25.0


def test_period_return_pct_edge() -> None:
    """None при отсутствии данных или нулевом первом закрытии."""

    assert math.period_return_pct(None, 100.0) is None
    assert math.period_return_pct(100.0, None) is None
    assert math.period_return_pct(0.0, 100.0) is None


def test_average() -> None:
    """Среднее арифметическое ряда."""

    assert math.average([1.0, 2.0, 3.0]) == 2.0
    assert math.average([]) is None


def test_average_return_pct_skips_none() -> None:
    """Среднее дневной доходности: None-значения пропускаются.

    (1.0 + 2.0 + 3.0) / 3 = 2.0.
    """

    assert math.average_return_pct([1.0, None, 2.0, 3.0]) == 2.0
    assert math.average_return_pct([None, None]) is None
    assert math.average_return_pct([]) is None


def test_sample_volatility_pct() -> None:
    """Выборочное стандартное отклонение (stddev_samp).

    Ряд [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]:
    среднее 5.0, сумма квадратов отклонений 32, дисперсия 32/7 = 4.571428...,
    stddev = 2.1380899... -> 2.1381 после округления до 4 знаков.
    """

    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    assert math.sample_volatility_pct(values) == pytest.approx(2.1381, abs=1e-4)


def test_sample_volatility_pct_simple() -> None:
    """Ряд [1.0, 3.0]: среднее 2, дисперсия ((1)+(1))/1 = 2, stddev 1.4142."""

    assert math.sample_volatility_pct([1.0, 3.0]) == pytest.approx(1.4142, abs=1e-4)


def test_sample_volatility_pct_small() -> None:
    """Для ряда из менее чем двух значений волатильность не определена."""

    assert math.sample_volatility_pct([]) is None
    assert math.sample_volatility_pct([5.0]) is None
    assert math.sample_volatility_pct([None, None]) is None


def test_max_drawdown_pct() -> None:
    """Просадка от пика к минимуму: 100 -> 120 -> 90 даёт 25 процентов."""

    assert math.max_drawdown_pct([100.0, 120.0, 90.0]) == 25.0


def test_max_drawdown_pct_monotonic_up() -> None:
    """Ряд только вверх: просадки нет, 0 процентов."""

    assert math.max_drawdown_pct([100.0, 110.0, 120.0]) == 0.0


def test_max_drawdown_pct_example() -> None:
    """Ряд 100 -> 80 -> 100 -> 70: хуже падение от 100 к 70, это 30 процентов."""

    assert math.max_drawdown_pct([100.0, 80.0, 100.0, 70.0]) == 30.0


def test_max_drawdown_pct_empty_and_single() -> None:
    """Пустой ряд даёт None, ряд из одного элемента даёт 0."""

    assert math.max_drawdown_pct([]) is None
    assert math.max_drawdown_pct([50.0]) == 0.0


def test_min_max_index() -> None:
    """Индексы минимума и максимума ряда."""

    assert math.min_max_index([3.0, 1.0, 5.0, 2.0]) == (1, 2)
    assert math.min_max_index([]) is None


def test_round_pct() -> None:
    """Округление процентов до 4 знаков."""

    assert math.round_pct(1.23456789) == 1.2346
    assert math.round_pct(None) is None
