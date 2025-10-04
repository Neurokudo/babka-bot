-- Скрипт для добавления колонки is_active в таблицу users
-- Выполните этот SQL в Railway PostgreSQL

-- Проверяем существование колонки is_active
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'is_active';

-- Если колонка не существует, добавляем её
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Проверяем структуру таблицы users
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Проверяем данные в таблице
SELECT * FROM users LIMIT 1;

-- Проверяем таблицу subscriptions
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'subscriptions'
ORDER BY ordinal_position;

-- Проверяем количество записей в subscriptions
SELECT COUNT(*) as subscription_count FROM subscriptions;
