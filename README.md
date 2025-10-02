# 🎭 Babka Bot - AI Video & Photo Generator

Telegram бот для генерации видео и обработки фотографий с помощью ИИ.

## 🚀 Быстрый деплой

### Railway
1. Форкните репозиторий
2. Создайте новый проект на Railway
3. Подключите GitHub репозиторий
4. Установите переменные окружения:
   - `TELEGRAM_BOT_TOKEN`
   - `YOOKASSA_SHOP_ID`
   - `YOOKASSA_SECRET_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS`
5. Railway автоматически задеплоит бота

### Render
1. Форкните репозиторий
2. Создайте новый Web Service на Render
3. Подключите GitHub репозиторий
4. Установите переменные окружения
5. Render автоматически задеплоит бота

### Локальный сервер
```bash
git clone https://github.com/your-username/babka-bot.git
cd babka-bot
chmod +x deploy.sh
./deploy.sh
```

## 💰 Монетизация

- **ЮKassa интеграция** готова к работе
- **Монетная система**: каждая генерация списывает монеты (видео/JSON — 10, фото — 1/2, примерочная — 1)
- **Тарифы**: Лайт (1 990 ₽ → 120 монет), Стандарт (2 490 ₽ → 210 монет), Про (4 990 ₽ → 440 монет)
- **Аддоны**: Video 5, Photo 20, Mix и др.

## 🎯 Функции

- 🎬 Генерация видео с помощью Veo 3
- 📸 Обработка фотографий (удаление фона, ретушь, Polaroid)
- 👗 Виртуальная примерочная

## 📋 Требования

- Python 3.13+
- Telegram Bot Token
- Google Cloud Platform API
- ЮKassa для платежей

## 🔧 Локальная разработка

```bash
git clone https://github.com/your-username/babka-bot.git
cd babka-bot
pip install -r requirements.txt
cp .env.example .env
# Заполните переменные окружения
python main.py
# Локальные unit-тесты
pytest tests/test_billing.py tests/test_plans.py
```

## 🗄️ Миграция базы данных

Для применения актуальной миграции выполните:

### Способ 1: Через psql (рекомендуется)
```bash
psql "postgres://<строка_подключения_из_Railway>" -f FINAL_MIGRATION.sql
```

### Способ 2: Через скрипт
```bash
# Bash скрипт
./apply_migration.sh "postgres://<строка_подключения_из_Railway>"

# Python скрипт (с проверкой результата)
python apply_migration.py "postgres://<строка_подключения_из_Railway>"
```

### Получение строки подключения из Railway:
1. Перейдите в ваш проект на Railway
2. Выберите PostgreSQL базу данных
3. Перейдите в раздел "Variables"
4. Скопируйте значение `DATABASE_URL`

Миграция:
- Приводит таблицу `users` к монетной модели (`coins`, `plan`, `plan_expiry`, `admin_coins`, `created_at`, `updated_at`)
- Очищает устаревшие бонусные поля и пересобирает `transactions` (только списания)
- Обновляет таблицу `payments` с полями `id`, `user_id`, `subscription_type`, `amount`, `status`, `created_at`, `idempotent_key`

## 📝 Лицензия

MIT License
