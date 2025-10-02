#!/usr/bin/env python3
"""
Быстрый деплой изменений
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Выполнить команду с описанием"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - успешно")
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ошибка")
        print(f"   {e.stderr.strip()}")
        return False

def main():
    """Основная функция деплоя"""
    print("🚀 Быстрый деплой исправлений платежей")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path("payment_yookassa.py").exists():
        print("❌ Файл payment_yookassa.py не найден. Запустите скрипт из корня проекта.")
        sys.exit(1)
    
    # Добавляем все изменения
    if not run_command("git add .", "Добавление изменений в git"):
        sys.exit(1)
    
    # Коммитим изменения
    commit_msg = "fix: исправлена проблема с return_url в платежах и добавлен webhook сервер"
    if not run_command(f'git commit -m "{commit_msg}"', "Создание коммита"):
        print("ℹ️  Возможно, нет изменений для коммита")
    
    # Пушим в репозиторий
    if not run_command("git push", "Отправка изменений в репозиторий"):
        print("⚠️  Не удалось отправить изменения. Проверьте настройки git.")
    
    print("\n📋 Что нужно сделать дальше:")
    print("1. Убедитесь, что Railway/Render автоматически задеплоил изменения")
    print("2. Проверьте логи деплоя на наличие ошибок")
    print("3. Настройте webhook в YooKassa:")
    print("   URL: https://ваш-домен.railway.app/webhook/yookassa")
    print("   События: payment.succeeded, payment.canceled")
    print("4. Протестируйте платеж")

if __name__ == "__main__":
    main()
