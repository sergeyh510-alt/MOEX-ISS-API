-- Подготовка к этапу 1: read-only роль и схемы.
-- Это всего лишь подготовка: реальные данные появляются в проекте DWH
-- (MOEX-ISS-mini-DWH), здесь только роль, схемы и гранты.
-- Пароль api_ro - dev-заглушка, в продакшене задаётся отдельно.

-- Read-only роль для API (если её ещё нет)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_ro') THEN
        CREATE ROLE api_ro LOGIN PASSWORD 'api_ro_dev_password';
    END IF;
END
$$;

-- Слои мини-DWH, которые читает API (если их ещё нет)
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS audit;

-- Доступ к схемам
GRANT USAGE ON SCHEMA mart TO api_ro;
GRANT USAGE ON SCHEMA core TO api_ro;
GRANT USAGE ON SCHEMA meta TO api_ro;
GRANT USAGE ON SCHEMA audit TO api_ro;

-- Чтение существующих таблиц
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA meta TO api_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO api_ro;

-- Чтение будущих таблиц (созданных владельцем схемы)
ALTER DEFAULT PRIVILEGES IN SCHEMA mart GRANT SELECT ON TABLES TO api_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT ON TABLES TO api_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA meta GRANT SELECT ON TABLES TO api_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT ON TABLES TO api_ro;
