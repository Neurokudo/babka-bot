#!/bin/bash

# Скрипт для применения миграции FINAL_MIGRATION.sql к Railway БД
# Использование: ./apply_migration.sh "postgres://user:password@host:port/database"

set -e  # Остановка при ошибке

MIGRATION_FILE="FINAL_MIGRATION.sql"

# Проверяем аргументы
if [ $# -eq 0 ]; then
    echo "❌ Ошибка: Не указана строка подключения к БД"
    echo ""
    echo "Использование:"
    echo "  $0 \"postgres://user:password@host:port/database\""
    echo ""
    echo "Пример:"
    echo "  $0 \"postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway\""
    echo ""
    echo "Получить строку подключения можно в Railway:"
    echo "1. Перейдите в ваш проект на Railway"
    echo "2. Выберите PostgreSQL базу данных"
    echo "3. Перейдите в раздел 'Variables'"
    echo "4. Скопируйте значение DATABASE_URL"
    exit 1
fi

DATABASE_URL="$1"

# Проверяем существование файла миграции
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Ошибка: Файл миграции $MIGRATION_FILE не найден!"
    exit 1
fi

echo "🚀 Применяем миграцию к Railway БД..."
echo "📁 Файл миграции: $MIGRATION_FILE"
echo "🔗 База данных: ${DATABASE_URL%%@*}@***"  # Скрываем пароль в логах
echo ""

# Применяем миграцию
echo "⏳ Выполняем миграцию..."
if psql "$DATABASE_URL" -f "$MIGRATION_FILE"; then
    echo ""
    echo "✅ Миграция успешно применена!"
    echo ""
    echo "📊 Что было сделано:"
    echo "  • Добавлена колонка admin_coins в таблицу users"
    echo "  • Установлены админские бонусы для ID = 5015100177: 30 видео, 50 фото, 10 примерочных, 500 админских монеток"
    echo "  • Исправлены старые пользователи с неправильными бонусами (2/3/1) на правильные (2/2/2)"
    echo ""
    echo "🎉 Система бонусов готова к работе!"
else
    echo ""
    echo "❌ Ошибка при применении миграции!"
    echo "Проверьте:"
    echo "  • Правильность строки подключения"
    echo "  • Доступность базы данных"
    echo "  • Права доступа к БД"
    exit 1
fi
