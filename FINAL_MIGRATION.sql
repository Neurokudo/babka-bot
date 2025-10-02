BEGIN;

-- Добавляем колонку admin_coins если её нет
ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_coins INTEGER NOT NULL DEFAULT 0;

-- Устанавливаем админские бонусы и монетки для админа (ID = 5015100177)
UPDATE users
SET admin_coins = 500,
    video_bonus = 30,
    photo_bonus = 50,
    tryon_bonus = 10
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

COMMIT;