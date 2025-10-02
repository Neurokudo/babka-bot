-- -*- coding: utf-8 -*-
-- Финальная схема БД для Babka Bot - только монеты и подписки

-- Таблица пользователей (упрощенная)
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    coins INT NOT NULL DEFAULT 0,
    plan VARCHAR(20) NOT NULL DEFAULT 'lite',
    plan_expiry TIMESTAMP NULL,
    admin_coins INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
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

-- Таблица транзакций (только списания)
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    operation_type TEXT NOT NULL,
    coins_spent INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индекс для быстрого поиска транзакций пользователя
CREATE INDEX IF NOT EXISTS idx_transactions_user_created 
ON transactions(user_id, created_at DESC);

-- Индекс для проверки истекших планов
CREATE INDEX IF NOT EXISTS idx_users_plan_expiry 
ON users(plan_expiry) WHERE plan_expiry IS NOT NULL;
