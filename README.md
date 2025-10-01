# 🎭 Babka Bot - AI Video & Photo Generator

Telegram бот для генерации видео и обработки фотографий с помощью ИИ.

## 🎁 Система подарочных генераций

Новые пользователи получают **3 бесплатных видео** и **3 бесплатных фото** для тестирования функционала!

## 🚀 Быстрый деплой

### Railway
1. Форкните репозиторий
2. Добавьте секреты в GitHub:
   - `RAILWAY_TOKEN` - токен Railway
   - `RAILWAY_SERVICE` - ID сервиса
3. Push в ветку `clean-main`
4. GitHub Actions автоматически задеплоит бота

### Render
1. Форкните репозиторий
2. Добавьте секреты в GitHub:
   - `RENDER_SERVICE_ID` - ID сервиса Render
   - `RENDER_API_KEY` - API ключ Render
3. Push в ветку `clean-main`
4. GitHub Actions автоматически задеплоит бота

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
