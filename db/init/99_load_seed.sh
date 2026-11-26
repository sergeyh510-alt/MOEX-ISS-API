#!/bin/sh
# Загрузка слепка витрин из db/seed при инициализации контейнера postgres.
# Файлы монтируются в /seed (только чтение).
# Если слепка нет, тихо выходим: это режим подключения к живому DWH.
#
# Скрипт обёрнут в функцию намеренно: официальный entrypoint postgres
# выполняет исполняемые *.sh как процесс, а неисполняемые подключает
# через source. Функция и return вместо exit делают скрипт безопасным в обоих
# случаях и не прерывают старт контейнера.
set -eu

seed_load() {
    SEED_DIR="/seed"

    if [ ! -d "$SEED_DIR" ]; then
        echo "seed: каталог $SEED_DIR не найден, пропускаем загрузку"
        return 0
    fi

    files=$(ls "$SEED_DIR"/*.sql 2>/dev/null || true)
    if [ -z "$files" ]; then
        echo "seed: файлов *.sql нет, пропускаем загрузку"
        return 0
    fi

    for f in "$SEED_DIR"/*.sql; do
        [ -e "$f" ] || continue
        echo "seed: применяю $f"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
    done

    # Повторно выдаём GRANT SELECT: на случай, если ALTER DEFAULT PRIVILEGES
    # не сработал до создания таблиц.
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
GRANT USAGE ON SCHEMA mart, core, meta, audit TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA meta TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO api_ro;
SQL

    echo "seed: загрузка слепка завершена"
    return 0
}

seed_load
