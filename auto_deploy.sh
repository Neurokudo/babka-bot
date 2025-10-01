#!/bin/bash

echo "🚀 Автоматический деплой бота..."

# Создаем бэкап
echo "📦 Создаем бэкап..."
backup_dir="/Users/msq/Desktop/archive/"
mkdir -p "$backup_dir"
current_time=$(date '+%Y-%m-%d %H:%M:%S')
backup_filename="main_backup_автодеплой_${current_time//[ :\-]/_}.py"
cp "main.py" "${backup_dir}${backup_filename}"
echo "✅ Бэкап создан: ${backup_dir}${backup_filename}"

# Git операции
echo "📁 Добавляем файлы в git..."
git add .

echo "💾 Создаем коммит..."
git commit -m "Автодеплой: $(date '+%Y-%m-%d %H:%M:%S')"

echo "🚀 Отправляем в GitHub..."
git push origin main

echo "✅ Деплой завершен!"
echo "📱 Проверьте бота в Telegram через 1-2 минуты"
