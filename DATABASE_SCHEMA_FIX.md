# Исправление схемы базы данных PostgreSQL

## 🚨 Проблема
После покупки подписки через YooKassa бот получает webhook (payment.succeeded), но не создаёт запись в таблице `subscriptions`. В логах Railway:
```
[ERROR] yookassa_service: Failed to create subscription for user XXXXX
```

**Причина:** Структура таблиц `users` и `subscriptions` в PostgreSQL не соответствует ожидаемой модели в коде.

## 🔧 Решение

### Вариант 1: Через Railway CLI (рекомендуется)

1. **Установите Railway CLI** (если не установлен):
   ```bash
   npm install -g @railway/cli
   ```

2. **Войдите в Railway**:
   ```bash
   railway login
   ```

3. **Подключитесь к проекту**:
   ```bash
   railway link
   ```

4. **Выполните Python скрипт**:
   ```bash
   railway run python fix_database_complete.py
   ```

### Вариант 2: Через Railway Dashboard

1. **Откройте Railway Dashboard** в браузере
2. **Перейдите в ваш проект** → **Database** → **Query**
3. **Выполните SQL команды** из файла `fix_subscriptions_schema.sql`

### Вариант 3: Через отдельные SQL команды

```sql
-- Исправление таблицы users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expiry TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Исправление таблицы subscriptions
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS user_id BIGINT NOT NULL;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS coins INTEGER DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS price_rub INTEGER NOT NULL;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS end_date TIMESTAMP NOT NULL;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_id TEXT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

## 📋 Ожидаемая структура таблиц

### Таблица `users`:
- `user_id` (BIGINT, PRIMARY KEY)
- `username` (TEXT)
- `first_name` (TEXT)
- `last_name` (TEXT)
- `coins` (INTEGER, DEFAULT 0)
- `plan` (TEXT)
- `plan_expiry` (TIMESTAMP)
- `auto_renew` (BOOLEAN, DEFAULT TRUE)
- `is_active` (BOOLEAN, DEFAULT TRUE)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### Таблица `subscriptions`:
- `id` (SERIAL, PRIMARY KEY)
- `user_id` (BIGINT, NOT NULL)
- `plan` (TEXT, NOT NULL)
- `coins` (INTEGER, DEFAULT 0)
- `price_rub` (INTEGER, NOT NULL)
- `start_date` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `end_date` (TIMESTAMP, NOT NULL)
- `is_active` (BOOLEAN, DEFAULT TRUE)
- `payment_id` (TEXT)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

## ✅ Проверка результата

После выполнения любого из вариантов:

1. **Перезапустите Railway контейнер**
2. **Проверьте логи** - ошибки `Failed to create subscription` должны исчезнуть
3. **Попробуйте купить подписку** через бота
4. **Убедитесь, что приходит уведомление** о подписке

## 🧪 Тестирование

```sql
-- Проверить структуру таблицы users
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Проверить структуру таблицы subscriptions
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'subscriptions'
ORDER BY ordinal_position;

-- Проверить данные в таблицах
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM subscriptions;

-- Тестировать INSERT в subscriptions
BEGIN;
INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id, created_at)
VALUES (999999999, 'test', 0, 0, '2025-01-01 00:00:00', '2025-01-02 00:00:00', TRUE, 'test-payment', '2025-01-01 00:00:00');
ROLLBACK;
```

## 🎯 Ожидаемый результат

- ✅ Все необходимые колонки добавлены в обе таблицы
- ✅ YooKassa webhook работает без ошибок
- ✅ Подписки создаются в таблице `subscriptions`
- ✅ Пользователи получают уведомления в Telegram
- ✅ Ошибка `Failed to create subscription` исчезает из логов
