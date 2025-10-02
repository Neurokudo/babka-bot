BEGIN;

-- Users --------------------------------------------------------------------

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS admin_coins INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS welcome_granted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'lite',
    ADD COLUMN IF NOT EXISTS plan_expiry TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS videos_allowed INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS photos_allowed INTEGER NOT NULL DEFAULT 0;

-- Поддерживаем устаревшие колонки, но переносим данные в новые поля
UPDATE users
SET videos_allowed = GREATEST(COALESCE(videos_allowed, 0), COALESCE(videos_left, 0))
WHERE COALESCE(videos_left, 0) <> 0;

UPDATE users
SET photos_allowed = GREATEST(COALESCE(photos_allowed, 0), COALESCE(photos_left, 0))
WHERE COALESCE(photos_left, 0) <> 0;

-- Обновляем план по умолчанию и дату окончания
UPDATE users
SET plan = 'lite'
WHERE plan IS NULL OR plan = '';

UPDATE users
SET plan_expiry = NULL
WHERE plan_expiry IS NOT NULL AND plan_expiry < '1970-01-01';

-- Гарантируем, что текущим пользователям приветственный бонус больше не начисляется
UPDATE users
SET welcome_granted = TRUE
WHERE welcome_granted IS DISTINCT FROM TRUE;

-- Устанавливаем админские бонусы и монетки для админа (ID = 5015100177)
UPDATE users
SET admin_coins = 500,
    video_bonus = 30,
    photo_bonus = 50,
    tryon_bonus = 10,
    welcome_granted = TRUE,
    videos_allowed = 30,
    photos_allowed = 50
WHERE user_id = 5015100177;

-- Исправляем старых пользователей с неправильными бонусами (2/3/1) на правильные (2/2/2)
UPDATE users
SET video_bonus = 2,
    photo_bonus = 2,
    tryon_bonus = 2
WHERE video_bonus = 2
  AND photo_bonus = 3
  AND tryon_bonus = 1
  AND user_id <> 5015100177;

-- Transactions --------------------------------------------------------------

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS before_value INTEGER,
    ADD COLUMN IF NOT EXISTS after_value INTEGER,
    ADD COLUMN IF NOT EXISTS delta INTEGER,
    ADD COLUMN IF NOT EXISTS reason VARCHAR(50),
    ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Payments -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(255) PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'RUB',
    plan VARCHAR(20),
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_idempotency
    ON payments (idempotency_key);

COMMIT;
