-- Схемы мини-DWH, которые читает API.
-- Файл идёт первым при загрузке слепка (db/init/99_load_seed.sh).
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS audit;
