-- -*- coding: utf-8 -*-
-- FINAL_MIGRATION.sql - Финальная миграция для Babka Bot
-- Упрощенная схема: только монеты и подписки

-- Проверяем, что миграция еще не применялась
INSERT INTO schema_migrations (version) VALUES ('final_migration_v2') 
ON CONFLICT (version) DO NOTHING;

-- Создаем таблицы если их нет
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    coins INT NOT NULL DEFAULT 0,
    plan VARCHAR(20) NOT NULL DEFAULT 'lite',
    plan_expiry TIMESTAMP NULL,
    admin_coins INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    subscription_type TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    idempotent_key TEXT UNIQUE NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    operation_type TEXT NOT NULL,
    coins_spent INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Удаляем старые колонки если они есть
ALTER TABLE users DROP COLUMN IF EXISTS video_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS photo_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS tryon_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS welcome_granted;
ALTER TABLE users DROP COLUMN IF EXISTS videos_left;
ALTER TABLE users DROP COLUMN IF EXISTS photos_left;
ALTER TABLE users DROP COLUMN IF EXISTS tryons_left;

-- Добавляем нужные колонки если их нет
ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'lite';
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expiry TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_coins INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- Создаем индексы если их нет
CREATE INDEX IF NOT EXISTS idx_transactions_user_created ON transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_plan_expiry ON users(plan_expiry) WHERE plan_expiry IS NOT NULL;

-- Удаляем старые таблицы если они есть
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS support_reports;

-- Upsert админа с правильными значениями
INSERT INTO users (user_id, coins, plan, plan_expiry, admin_coins)
VALUES (5015100177, 0, 'lite', NULL, 500)
ON CONFLICT (user_id) DO UPDATE SET
    admin_coins = 500,
    updated_at = NOW();

-- Обновляем updated_at для всех записей
UPDATE users SET updated_at = NOW() WHERE updated_at < created_at;