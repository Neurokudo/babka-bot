# Исправление схемы базы данных в Railway

## 🚨 Проблема
В таблице `users` отсутствует колонка `is_active`, что вызывает ошибки при создании подписок.

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

4. **Выполните SQL команду**:
   ```bash
   railway run psql -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;"
   ```

5. **Проверьте результат**:
   ```bash
   railway run psql -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_active';"
   ```

### Вариант 2: Через Railway Dashboard

1. **Откройте Railway Dashboard** в браузере
2. **Перейдите в ваш проект** → **Database** → **Query**
3. **Выполните SQL команду**:
   ```sql
   ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
   ```

4. **Проверьте результат**:
   ```sql
   SELECT column_name, data_type, is_nullable, column_default
   FROM information_schema.columns 
   WHERE table_name = 'users'
   ORDER BY ordinal_position;
   ```

### Вариант 3: Через Python скрипт в Railway

1. **Загрузите скрипт** `railway_fix_schema.py` в Railway
2. **Выполните скрипт**:
   ```bash
   railway run python railway_fix_schema.py
   ```

## ✅ Проверка результата

После выполнения любого из вариантов:

1. **Перезапустите Railway контейнер**
2. **Проверьте логи** - ошибка `column users.is_active does not exist` должна исчезнуть
3. **Попробуйте купить подписку** через бота
4. **Убедитесь, что приходит уведомление** о подписке

## 🎯 Ожидаемый результат

- ✅ Колонка `is_active` добавлена в таблицу `users`
- ✅ Webhook от YooKassa работает без ошибок
- ✅ Подписки создаются в базе данных
- ✅ Пользователи получают уведомления в Telegram

## 📋 SQL команды для проверки

```sql
-- Проверить структуру таблицы users
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Проверить данные в таблице users
SELECT user_id, username, is_active FROM users LIMIT 5;

-- Проверить таблицу subscriptions
SELECT COUNT(*) FROM subscriptions;

-- Проверить последние подписки
SELECT user_id, plan, is_active, created_at 
FROM subscriptions 
ORDER BY created_at DESC 
LIMIT 5;
```
