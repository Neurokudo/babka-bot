# 🎭 Babka Bot - AI Video & Photo Generator

Telegram бот для генерации видео и обработки фотографий с помощью ИИ.

## 🎁 Система подарочных генераций

Новые пользователи получают **3 бесплатных видео** и **3 бесплатных фото** для тестирования функционала!

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
- **Тарифы**: Лайт (1990₽), Стандарт (2490₽), Про (4990₽)
- **Докупки**: Video 5, Photo 20, Mix пакеты
- **Внутренняя валюта**: Монетки

## 🎯 Функции

- 🎬 Генерация видео с помощью Veo 3
- 📸 Обработка фотографий (удаление фона, ретушь, Polaroid)
- 👗 Виртуальная примерочная
- 🎁 Бесплатные бонусы для новых пользователей

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
```

## 📝 Лицензия

MIT License
