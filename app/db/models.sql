-- -*- coding: utf-8 -*-
-- Финальная схема БД для Babka Bot - новая система кошелька

-- Таблица пользователей (упрощенная)
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица кошелька пользователей
CREATE TABLE IF NOT EXISTS users_wallet (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
    coins_balance INT NOT NULL DEFAULT 0,
    active_tariff TEXT,            -- lite|standard|pro|NULL
    tariff_expires_at TIMESTAMP    -- NULL если нет активной подписки
);

-- Таблица платежей
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    subscription_type TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    idempotent_key TEXT UNIQUE NULL
);

-- Таблица транзакций кошелька (операции/аналитика)
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    kind TEXT NOT NULL,            -- "tariff_purchase"|"topup_purchase"|"feature_charge"
    feature_key TEXT,              -- NULL для покупок, иначе "video_8s_audio" и т.д.
    coins_delta INT NOT NULL,      -- + начисление / - списание
    rub_value NUMERIC(12,2),       -- сколько стоило пользователю (если применимо)
    cogs_usd NUMERIC(12,2),        -- твоя себестоимость (если применимо)
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индекс для быстрого поиска транзакций пользователя
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_created 
ON wallet_transactions(user_id, created_at DESC);

-- Индекс для проверки истекших тарифов
CREATE INDEX IF NOT EXISTS idx_users_wallet_tariff_expiry 
ON users_wallet(tariff_expires_at) WHERE tariff_expires_at IS NOT NULL;

-- Индекс для аналитики по функциям
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_feature 
ON wallet_transactions(feature_key, created_at DESC) WHERE feature_key IS NOT NULL;
