"""Сборка схем цен, доходности и сводки по бумаге из строк моделей.

Чистая математика лежит в app.services.returns, здесь только приведение
строк БД к схемам ответа.
"""

from datetime import date

from app.models.core import FactDailyIndex, FactDailyPrice
from app.models.mart import IndexCompare, StockReturn
from app.schemas.compare import CompareRow
from app.schemas.indices import IndexBar, IndexInfo
from app.schemas.prices import PriceBar
from app.schemas.returns import ClosePoint, DayReturn, ReturnRow, Summary
from app.services import returns as math
from app.services.dates import date_key_to_date


def _as_float(value) -> float | None:
    """Привести numeric/Decimal к float (None остаётся None)."""

    if value is None:
        return None
    return float(value)


def to_price_bar(row: FactDailyPrice) -> PriceBar:
    """Преобразовать строку core.fact_daily_prices в схему PriceBar."""

    return PriceBar(
        date=date_key_to_date(row.date_key),
        date_key=row.date_key,
        open=_as_float(row.open),
        low=_as_float(row.low),
        high=_as_float(row.high),
        close=_as_float(row.close),
        waprice=_as_float(row.waprice),
        value=_as_float(row.value),
        volume=row.volume,
        numtrades=row.numtrades,
        prev_close=_as_float(row.prev_close),
        close_change=_as_float(row.close_change),
        close_change_pct=_as_float(row.close_change_pct),
    )


def to_return_row(row: StockReturn) -> ReturnRow:
    """Преобразовать строку mart.stock_returns в схему ReturnRow."""

    return ReturnRow(
        date=date_key_to_date(row.date_key),
        date_key=row.date_key,
        close=_as_float(row.close),
        prev_close=_as_float(row.prev_close),
        daily_return_pct=_as_float(row.daily_return_pct),
        gap_pct=_as_float(row.gap_pct),
        amplitude_pct=_as_float(row.amplitude_pct),
        ma_5=_as_float(row.ma_5),
        ma_20=_as_float(row.ma_20),
        volatility_5_pct=_as_float(row.volatility_5_pct),
        volatility_20_pct=_as_float(row.volatility_20_pct),
        cumulative_return_pct=_as_float(row.cumulative_return_pct),
    )


def to_index_info(index_code: str, first_date_key: int, last_date_key: int, rows: int) -> IndexInfo:
    """Собрать сводку по индексу из агрегатов витрины."""

    return IndexInfo(
        index_code=index_code,
        first_date=date_key_to_date(first_date_key),
        last_date=date_key_to_date(last_date_key),
        rows=rows,
    )


def to_index_bar(row: FactDailyIndex) -> IndexBar:
    """Преобразовать строку core.fact_daily_index в схему IndexBar."""

    return IndexBar(
        date=date_key_to_date(row.date_key),
        date_key=row.date_key,
        open=_as_float(row.open),
        low=_as_float(row.low),
        high=_as_float(row.high),
        close=_as_float(row.close),
        value=_as_float(row.value),
        prev_close=_as_float(row.prev_close),
        close_change=_as_float(row.close_change),
        close_change_pct=_as_float(row.close_change_pct),
    )


def to_compare_row(row: IndexCompare) -> CompareRow:
    """Преобразовать строку mart.index_compare в схему CompareRow."""

    return CompareRow(
        date=date_key_to_date(row.date_key),
        date_key=row.date_key,
        secid=row.secid,
        index_code=row.index_code,
        stock_return_pct=_as_float(row.stock_return_pct),
        index_return_pct=_as_float(row.index_return_pct),
        excess_return_pct=_as_float(row.excess_return_pct),
    )


def _extreme_day(rows: list[StockReturn], *, best: bool) -> DayReturn | None:
    """День с максимальной (best) или минимальной (worst) доходностью."""

    candidates = [row for row in rows if row.daily_return_pct is not None]
    if not candidates:
        return None
    picker = max if best else min
    picked = picker(candidates, key=lambda row: row.daily_return_pct)
    return DayReturn(
        date=date_key_to_date(picked.date_key),
        daily_return_pct=math.round_pct(_as_float(picked.daily_return_pct)),
    )


def _extreme_close(rows: list[StockReturn], *, highest: bool) -> ClosePoint | None:
    """День с максимальной (highest) или минимальной ценой закрытия."""

    if not rows:
        return None
    picker = max if highest else min
    picked = picker(rows, key=lambda row: row.close)
    return ClosePoint(
        date=date_key_to_date(picked.date_key),
        close=_as_float(picked.close),
    )


def build_summary(
    *,
    secid: str,
    boardid: str,
    rows: list[StockReturn],
    from_date: date | None,
    to_date: date | None,
) -> Summary:
    """Собрать сводку по бумаге за период из строк mart.stock_returns.

    Строки должны идти в порядке возрастания даты. Если строк нет, метрики
    равны null, а trading_days равен нулю. Даты периода: фактические границы
    данных, а при их отсутствии запрошенный период.
    """

    trading_days = len(rows)

    if not rows:
        return Summary(
            secid=secid,
            boardid=boardid,
            from_date=from_date,
            to_date=to_date,
            trading_days=0,
            first_close=None,
            last_close=None,
            period_return_pct=None,
            cumulative_return_pct=None,
            avg_daily_return_pct=None,
            volatility_pct=None,
            best_day=None,
            worst_day=None,
            max_close=None,
            min_close=None,
            max_drawdown_pct=None,
        )

    closes = [float(row.close) for row in rows]
    returns = [_as_float(row.daily_return_pct) for row in rows]

    first_close = closes[0]
    last_close = closes[-1]
    effective_from = date_key_to_date(rows[0].date_key)
    effective_to = date_key_to_date(rows[-1].date_key)

    return Summary(
        secid=secid,
        boardid=boardid,
        from_date=effective_from,
        to_date=effective_to,
        trading_days=trading_days,
        first_close=first_close,
        last_close=last_close,
        period_return_pct=math.period_return_pct(first_close, last_close),
        cumulative_return_pct=math.round_pct(_as_float(rows[-1].cumulative_return_pct)),
        avg_daily_return_pct=math.average_return_pct(returns),
        volatility_pct=math.sample_volatility_pct(returns),
        best_day=_extreme_day(rows, best=True),
        worst_day=_extreme_day(rows, best=False),
        max_close=_extreme_close(rows, highest=True),
        min_close=_extreme_close(rows, highest=False),
        max_drawdown_pct=math.max_drawdown_pct(closes),
    )
