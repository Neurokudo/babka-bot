#!/usr/bin/env python3
"""
Быстрый коммит - просто запустите с описанием изменений
"""

import sys
import subprocess
from datetime import datetime

def quick_commit():
    """Быстрый коммит с автоматическим сообщением"""
    if len(sys.argv) < 2:
        print("❌ Укажите описание изменений")
        print("Пример: python3 quick_commit.py 'Добавил новую функцию'")
        return
    
    message = " ".join(sys.argv[1:])
    
    try:
        # Git add
        subprocess.run(["git", "add", "."], check=True)
        
        # Git commit
        subprocess.run(["git", "commit", "-m", message], check=True)
        
        # Git push
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print(f"✅ Коммит '{message}' успешно отправлен!")
        
        # Создаем бэкап с русским названием
        backup_dir = "/Users/msq/Desktop/archive"
        if os.path.exists(backup_dir):
            safe_filename = message.replace(" ", "_").replace(":", "").replace("-", "")
            backup_file = f"{backup_dir}/main_backup_{safe_filename}.py"
            try:
                subprocess.run(["cp", "main.py", backup_file], check=True)
                print(f"📦 Бэкап создан: {backup_file}")
            except subprocess.CalledProcessError:
                print("⚠️ Не удалось создать бэкап")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    quick_commit()
