-- -*- coding: utf-8 -*-
-- Миграция к новой системе кошелька
-- Выполнить этот скрипт для обновления существующей БД

-- 1. Создаем новые таблицы если их нет
CREATE TABLE IF NOT EXISTS users_wallet (
    user_id BIGINT PRIMARY KEY,
    coins_balance INT NOT NULL DEFAULT 0,
    active_tariff TEXT,            -- lite|standard|pro|NULL
    tariff_expires_at TIMESTAMP    -- NULL если нет активной подписки
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    kind TEXT NOT NULL,            -- "tariff_purchase"|"topup_purchase"|"feature_charge"
    feature_key TEXT,              -- NULL для покупок, иначе "video_8s_audio" и т.д.
    coins_delta INT NOT NULL,      -- + начисление / - списание
    rub_value NUMERIC(12,2),       -- сколько стоило пользователю (если применимо)
    cogs_usd NUMERIC(12,2),        -- твоя себестоимость (если применимо)
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. Мигрируем данные из старой таблицы users в новую users_wallet
INSERT INTO users_wallet (user_id, coins_balance, active_tariff, tariff_expires_at)
SELECT 
    user_id,
    COALESCE(coins, 0) as coins_balance,
    CASE 
        WHEN plan = 'lite' THEN 'lite'
        WHEN plan = 'standard' THEN 'standard' 
        WHEN plan = 'pro' THEN 'pro'
        ELSE NULL
    END as active_tariff,
    plan_expiry as tariff_expires_at
FROM users
WHERE user_id IS NOT NULL
ON CONFLICT (user_id) DO UPDATE SET
    coins_balance = EXCLUDED.coins_balance,
    active_tariff = EXCLUDED.active_tariff,
    tariff_expires_at = EXCLUDED.tariff_expires_at;

-- 3. Создаем индексы для производительности
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_created 
ON wallet_transactions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_wallet_tariff_expiry 
ON users_wallet(tariff_expires_at) WHERE tariff_expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_wallet_transactions_feature 
ON wallet_transactions(feature_key, created_at DESC) WHERE feature_key IS NOT NULL;

-- 4. Логируем миграцию
INSERT INTO wallet_transactions (user_id, kind, coins_delta, rub_value, created_at)
SELECT 
    user_id,
    'migration_balance',
    COALESCE(coins, 0),
    0,
    NOW()
FROM users
WHERE COALESCE(coins, 0) > 0;

-- 5. Обновляем существующие транзакции (если есть таблица transactions)
-- Мигрируем старые транзакции в новый формат
INSERT INTO wallet_transactions (user_id, kind, coins_delta, rub_value, created_at)
SELECT 
    user_id,
    CASE 
        WHEN kind = 'debit' THEN 'feature_charge'
        WHEN kind = 'credit' THEN 'topup_purchase'
        ELSE 'legacy_transaction'
    END as kind,
    delta as coins_delta,
    NULL as rub_value,
    created_at
FROM transactions
WHERE what = 'coins'
ON CONFLICT DO NOTHING;

-- 6. Проверяем результат
SELECT 
    'Migration completed' as status,
    COUNT(*) as total_users,
    SUM(coins_balance) as total_coins
FROM users_wallet;
