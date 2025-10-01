#!/usr/bin/env python3
"""
Помощник для автоматического коммита в git
"""

import subprocess
import sys
import os
from datetime import datetime

def auto_commit(message=None):
    """
    Автоматически коммитит все изменения в git
    
    Args:
        message (str): Сообщение коммита. Если None, создается автоматическое
    """
    if message is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Обновление от {timestamp}"
    
    try:
        # Добавляем все файлы
        print("📁 Добавляем файлы в git...")
        result = subprocess.run(["git", "add", "."], 
                              capture_output=True, text=True, check=True)
        
        # Проверяем, есть ли изменения
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("ℹ️ Нет изменений для коммита")
            return True
        
        # Создаем коммит
        print(f"💾 Создаем коммит: {message}")
        result = subprocess.run(["git", "commit", "-m", message], 
                              capture_output=True, text=True, check=True)
        
        # Пушим в репозиторий
        print("🚀 Отправляем в репозиторий...")
        result = subprocess.run(["git", "push", "origin", "main"], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Изменения успешно сохранены в git!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка git: {e}")
        if e.stderr:
            print(f"Детали: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def auto_commit_with_backup(message=None):
    """
    Создает бэкап в папку archive и коммитит изменения
    """
    if message is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Обновление от {timestamp}"
    
    # Создаем бэкап с русским названием
    backup_dir = "/Users/msq/Desktop/archive"
    if os.path.exists(backup_dir):
        # Используем сообщение коммита как название бэкапа
        safe_filename = message.replace(" ", "_").replace(":", "").replace("-", "")
        backup_file = f"{backup_dir}/main_backup_{safe_filename}.py"
        
        try:
            subprocess.run(["cp", "main.py", backup_file], check=True)
            print(f"📦 Бэкап создан: {backup_file}")
        except subprocess.CalledProcessError:
            print("⚠️ Не удалось создать бэкап")
    
    # Коммитим изменения
    return auto_commit(message)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        auto_commit_with_backup(message)
    else:
        auto_commit_with_backup()
