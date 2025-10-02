-- ФИНАЛЬНАЯ МИГРАЦИЯ ДЛЯ СИСТЕМЫ БОНУСОВ
-- Выполнить на Railway через: railway connect -> psql

-- 1. Добавляем колонку admin_coins если её нет
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='admin_coins'
    ) THEN
        ALTER TABLE users ADD COLUMN admin_coins INTEGER DEFAULT 0;
        RAISE NOTICE 'Added admin_coins column';
    ELSE
        RAISE NOTICE 'admin_coins column already exists';
    END IF;
END $$;

-- 2. Устанавливаем админу 500 админских монет
UPDATE users 
SET admin_coins = 500 
WHERE user_id = 5015100177;

-- 3. Исправляем исторические данные: если точно 2/3/1 -> 2/2/2
UPDATE users 
SET photo_bonus = 2, tryon_bonus = 2
WHERE video_bonus = 2 AND photo_bonus = 3 AND tryon_bonus = 1;

-- 4. Показываем результат для админа
SELECT 
    user_id,
    coins,
    video_bonus,
    photo_bonus, 
    tryon_bonus,
    admin_coins,
    plan
FROM users 
WHERE user_id = 5015100177;

-- 5. Показываем всех пользователей с их бонусами
SELECT 
    user_id,
    video_bonus,
    photo_bonus,
    tryon_bonus,
    COALESCE(admin_coins, 0) as admin_coins
FROM users 
ORDER BY user_id;
