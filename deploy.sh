#!/bin/bash

# Скрипт для деплоя бота на сервер
echo "🚀 Начинаем деплой Babka Bot..."

# Проверяем зависимости
echo "📦 Проверяем зависимости..."
pip install -r requirements.txt

# Проверяем переменные окружения
echo "🔧 Проверяем конфигурацию..."
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN не установлен"
    exit 1
fi

if [ -z "$YOOKASSA_SHOP_ID" ]; then
    echo "❌ YOOKASSA_SHOP_ID не установлен"
    exit 1
fi

if [ -z "$YOOKASSA_SECRET_KEY" ]; then
    echo "❌ YOOKASSA_SECRET_KEY не установлен"
    exit 1
fi

echo "✅ Все переменные окружения настроены"

# Запускаем бота
echo "🎭 Запускаем Babka Bot..."
echo "🎁 Система подарочных генераций активна"
echo "💰 ЮKassa интеграция готова к работе"

python main.py
