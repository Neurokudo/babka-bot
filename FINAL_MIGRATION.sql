BEGIN;

-- Users ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    coins INTEGER NOT NULL DEFAULT 0,
    plan VARCHAR(20) NOT NULL DEFAULT 'lite',
    plan_expiry TIMESTAMP NULL,
    admin_coins INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS coins INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'lite',
    ADD COLUMN IF NOT EXISTS plan_expiry TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS admin_coins INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

ALTER TABLE users DROP COLUMN IF EXISTS video_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS photo_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS tryon_bonus;
ALTER TABLE users DROP COLUMN IF EXISTS videos_allowed;
ALTER TABLE users DROP COLUMN IF EXISTS photos_allowed;
ALTER TABLE users DROP COLUMN IF EXISTS videos_left;
ALTER TABLE users DROP COLUMN IF EXISTS photos_left;
ALTER TABLE users DROP COLUMN IF EXISTS daily_date;
ALTER TABLE users DROP COLUMN IF EXISTS daily_videos;

-- Transactions --------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    operation_type VARCHAR(50) NOT NULL,
    coins_spent INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE transactions
    DROP COLUMN IF EXISTS used_bonus,
    DROP COLUMN IF EXISTS bonus_type,
    DROP COLUMN IF EXISTS quality,
    DROP COLUMN IF EXISTS before_value,
    DROP COLUMN IF EXISTS after_value,
    DROP COLUMN IF EXISTS delta,
    DROP COLUMN IF EXISTS reason,
    DROP COLUMN IF EXISTS metadata,
    DROP COLUMN IF EXISTS completed_at,
    DROP COLUMN IF EXISTS error_at;

-- Payments ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    subscription_type VARCHAR(50),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    idempotent_key VARCHAR(255) UNIQUE
);

DROP TABLE IF EXISTS processed_payments;

COMMIT;
