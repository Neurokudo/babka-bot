# 🗄️ Настройка PostgreSQL базы данных

## 🚀 Быстрая настройка на Railway

### 1. Создание базы данных на Railway

1. **Перейдите на [Railway.app](https://railway.app)**
2. **Войдите через GitHub**
3. **Нажмите "New Project"**
4. **Выберите "Provision PostgreSQL"**
5. **Дождитесь создания базы данных**

### 2. Получение строки подключения

1. **Кликните на созданную базу данных PostgreSQL**
2. **Перейдите в раздел "Variables"**
3. **Скопируйте значение `DATABASE_URL`** (выглядит как `postgresql://postgres:password@host:port/database`)

### 3. Настройка переменной окружения

#### Для локальной разработки:
```bash
# Добавьте в файл .env
DATABASE_URL=postgresql://postgres:password@host:port/database
```

#### Для Render (продакшн):
1. **Перейдите в настройки вашего сервиса на Render**
2. **Environment Variables**
3. **Добавьте переменную:**
   - **Key:** `DATABASE_URL`
   - **Value:** `postgresql://postgres:password@host:port/database`

### 4. Проверка подключения

База данных автоматически создаст нужные таблицы при первом запуске бота.

## 📊 Структура базы данных

### Таблица `users`
- `user_id` (BIGINT) — ID пользователя Telegram
- `coins` (INTEGER) — текущий баланс монет
- `admin_coins` (INTEGER) — служебный баланс для админа
- `plan` (VARCHAR) — активный тариф (`lite` по умолчанию)
- `plan_expiry` (TIMESTAMP) — срок действия тарифа
- `created_at` / `updated_at` (TIMESTAMP) — метаданные

### Таблица `transactions`
- `id` (SERIAL) - уникальный ID транзакции
- `user_id` (BIGINT) - ID пользователя
- `operation_type` (VARCHAR) - тип операции
- `coins_spent` (INTEGER) - потрачено монет
- `quality` (VARCHAR) - качество обработки
- `status` (VARCHAR) - статус (pending/completed/error)
- `created_at` (TIMESTAMP) - дата создания
- `completed_at` (TIMESTAMP) - дата завершения
- `error_at` (TIMESTAMP) - дата ошибки
- `before_value` / `after_value` / `delta` — движение баланса
- `reason`, `metadata` — причина и дополнительная информация

## 🔧 Альтернативные варианты

### Supabase (бесплатно до 500MB)
1. **Перейдите на [supabase.com](https://supabase.com)**
2. **Создайте новый проект**
3. **Перейдите в Settings → Database**
4. **Скопируйте Connection string**

### Neon (бесплатно до 3GB)
1. **Перейдите на [neon.tech](https://neon.tech)**
2. **Создайте новый проект**
3. **Скопируйте Connection string**

### Render (бесплатно до 1GB)
1. **Перейдите на [render.com](https://render.com)**
2. **Создайте PostgreSQL service**
3. **Скопируйте External Database URL**

## ⚠️ Важные замечания

- **Все данные сохраняются автоматически** после каждой операции
- **База данных создает резервные копии** каждые 4 часа
- **Данные не теряются** при перезапуске бота
- **История всех операций** сохраняется для аналитики

## 🆘 Поддержка

Если возникли проблемы с настройкой базы данных:
1. Проверьте правильность `DATABASE_URL`
2. Убедитесь, что база данных доступна из интернета
3. Проверьте логи бота на ошибки подключения
