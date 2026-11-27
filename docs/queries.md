# Ключевые SQL-запросы

Все запросы только читают (`SELECT`), их собирают репозитории
`app/repositories` через SQLAlchemy Core. Ниже показан эквивалентный SQL и
пояснения: что запрос делает, на что опирается (индексы, сортировка),
как обрабатывает `NULL`.

`date_key` это целое `YYYYMMDD`, поэтому период передаётся как границы int,
а не как дата.

## 1. Справочник бумаг с поиском

```sql
SELECT security_key, secid, boardid, shortname, first_tradedate, last_tradedate
FROM core.dim_security
WHERE (secid ILIKE '%sber%' OR shortname ILIKE '%sber%')
  AND boardid = 'TQBR'
ORDER BY secid ASC, boardid ASC
LIMIT 10 OFFSET 0;
```

Поиск регистронезависимый (`ILIKE`) по `secid` и `shortname`, фильтр по
`boardid` точный. Сортировка по выбранной колонке, вторичный ключ `boardid`,
чтобы порядок был стабильным при одной `secid` на нескольких бордах. Общее
число строк по фильтру считается отдельным `count`.

## 2. Цены за период

```sql
SELECT *
FROM core.fact_daily_prices
WHERE security_key = :security_key
  AND date_key >= :from_key
  AND date_key <= :to_key
ORDER BY date_key ASC
LIMIT 100 OFFSET 0;
```

Бумага сначала разрешается по `secid` (при нескольких бордах берётся строка с
самым поздним `last_tradedate`), затем читаются цены по `security_key`.
Составной PK `(security_key, date_key)` даёт индекс, покрывающий и фильтр, и
сортировку по `date_key`. Границы периода необязательны: без `from` / `to`
условия просто не добавляются.

## 3. Агрегат summary по бумаге

```sql
SELECT
  count(*)                                   AS trading_days,
  min(date_key)                              AS first_date_key,
  max(date_key)                              AS last_date_key,
  avg(daily_return_pct)                      AS avg_daily_return_pct,
  stddev_samp(daily_return_pct)              AS volatility_pct
FROM mart.stock_returns
WHERE security_key = :security_key
  AND date_key >= :from_key
  AND date_key <= :to_key;
```

Помимо агрегатов сервис читает ряд `close` в порядке `date_key` и считает
периодную доходность, лучший и худший день, максимум и минимум close и
просадку функцией `max_drawdown_pct` (`app/services/returns.py`). `stddev_samp`
это выборочное стандартное отклонение; при `NULL` в `daily_return_pct`
агрегаты `avg` / `stddev_samp` эти строки пропускают. `stddev_samp` для менее
чем двух значений даёт `NULL`, это норма.

## 4. Просадка (расчёт в сервисе)

Просадку считает не SQL, а чистая функция по ряду `close` в порядке даты:
проходим ряд, помним достигнутый пик и берём максимум падения от пика,
результат положительный (12.5 значит падение на 12.5 процента). Вынос в
`app/services/returns.py` нужен, чтобы это покрывалось юнит-тестами и было
общим для PostgreSQL и ClickHouse.

## 5. Рейтинг с оконными функциями

В PostgreSQL сервис читает строки окна и считает агрегаты в Python
(`app/services/ranking.py`), а место в рейтинге берётся из окна:

```sql
SELECT
  security_key,
  secid,
  boardid,
  count(*)                        AS trading_days,
  min(close)                      AS first_close,
  max(close)                      AS last_close,
  avg(daily_return_pct)           AS avg_daily_return_pct,
  stddev_samp(daily_return_pct)   AS volatility_pct,
  ROW_NUMBER() OVER (
    ORDER BY avg(daily_return_pct) DESC
  )                               AS rank
FROM mart.stock_returns
WHERE date_key >= :from_key AND date_key <= :to_key
GROUP BY security_key, secid, boardid
ORDER BY rank
LIMIT 10 OFFSET 0;
```

`ROW_NUMBER()` задаёт порядок по выбранной метрике (`period_return`,
`avg_daily_return`, `volatility`, `cumulative_return`) и направлению
`asc` / `desc`. Ранг нумеруется с 1 и учитывает `offset`. `min(close)` это не
первая цена по времени, поэтому первая и последняя цена берутся по
минимальному и максимальному `date_key`.

## 6. Поиск лучших и худших дней

```sql
-- день: лучшие бумаги
SELECT *
FROM mart.daily_movers
WHERE date_key = :date_key
ORDER BY daily_return_pct DESC, secid ASC
LIMIT 5;

-- день: худшие бумаги
SELECT *
FROM mart.daily_movers
WHERE date_key = :date_key
ORDER BY daily_return_pct ASC, secid ASC
LIMIT 5;
```

Вторичный ключ `secid ASC` даёт стабильный порядок при равной доходности.
Важно: в PostgreSQL `ORDER BY ... DESC` по умолчанию ставит `NULL` первыми,
поэтому при наличии `NULL` в `daily_return_pct` его надо явно отодвигать
(`NULLS LAST`), иначе первым вернётся `NULL`.

## 7. Сравнение с индексом

```sql
SELECT date_key, secid, index_code,
       stock_return_pct, index_return_pct, excess_return_pct
FROM mart.index_compare
WHERE security_key = :security_key
  AND lower(index_code) = lower(:index_code)
  AND date_key >= :from_key
  AND date_key <= :to_key
ORDER BY date_key ASC
LIMIT 100 OFFSET 0;
```

Код индекса сравнивается без учёта регистра (`lower`), а наружу отдаётся так,
как записан в БД. `excess_return_pct` это превышение доходности бумаги над
индексом за день (stock минус index). Составной PK
`(index_code, security_key, date_key)` покрывает фильтр и сортировку.
