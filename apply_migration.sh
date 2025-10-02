#!/bin/bash
# Автоматическое применение миграций при деплое на Railway

set -e

echo "🚀 Starting deployment with automatic migration..."

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found. Skipping migration."
    exit 0
fi

echo "📊 Applying database migration..."

# Применяем миграцию
if psql "$DATABASE_URL" -f FINAL_MIGRATION.sql; then
    echo "✅ Migration applied successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

echo "🎉 Deployment completed successfully!"