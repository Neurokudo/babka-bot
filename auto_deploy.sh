#!/bin/bash

set -euo pipefail

echo "🚀 Автоматический деплой бота..."

# Путь для резервных копий можно переопределить переменной BACKUP_DIR
backup_dir=${BACKUP_DIR:-"./backups"}
mkdir -p "${backup_dir}"

current_time=$(date -u '+%Y-%m-%dT%H-%M-%SZ')
backup_filename="main_backup_${current_time}.py"
cp "main.py" "${backup_dir}/${backup_filename}"
echo "✅ Бэкап main.py: ${backup_dir}/${backup_filename}"

# Git операции
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "📁 Добавляем файлы в git..."
  git add .
else
  echo "ℹ️ Нет изменений для коммита — деплой пропущен"
  exit 0
fi

echo "💾 Создаем коммит..."
commit_message="Автодеплой: ${current_time}"
git commit -m "${commit_message}" || {
  echo "❌ Не удалось создать коммит" >&2
  exit 1
}

echo "🚀 Отправляем в GitHub..."
git push origin main

echo "✅ Деплой завершен!"
echo "📱 Проверьте бота в Telegram через 1-2 минуты"
