-- Скрипт для исправления структуры таблицы subscriptions в PostgreSQL
-- Выполните этот SQL в Railway PostgreSQL

-- Проверяем текущую структуру таблицы subscriptions
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'subscriptions'
ORDER BY ordinal_position;

-- Добавляем недостающие колонки (если они отсутствуют)

-- 1. Добавляем колонку id (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;

-- 2. Добавляем колонку user_id (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS user_id BIGINT NOT NULL;

-- 3. Добавляем колонку plan (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL;

-- 4. Добавляем колонку coins (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS coins INTEGER DEFAULT 0;

-- 5. Добавляем колонку price_rub (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS price_rub INTEGER NOT NULL;

-- 6. Добавляем колонку start_date (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 7. Добавляем колонку end_date (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS end_date TIMESTAMP NOT NULL;

-- 8. Добавляем колонку is_active (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 9. Добавляем колонку payment_id (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_id TEXT;

-- 10. Добавляем колонку created_at (если отсутствует)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Проверяем финальную структуру таблицы subscriptions
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'subscriptions'
ORDER BY ordinal_position;

-- Проверяем количество записей в таблице
SELECT COUNT(*) as subscription_count FROM subscriptions;

-- Проверяем последние записи (если есть)
SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 5;

-- Тестируем INSERT запрос (не сохраняем)
BEGIN;
INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id, created_at)
VALUES (999999999, 'test', 0, 0, '2025-01-01 00:00:00', '2025-01-02 00:00:00', TRUE, 'test-payment', '2025-01-01 00:00:00');
ROLLBACK; -- Откатываем тестовую запись

-- Проверяем, что таблица готова к работе
SELECT 'Table subscriptions is ready for use' as status;
