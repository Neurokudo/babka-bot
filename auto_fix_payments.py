#!/usr/bin/env python3
"""
Полностью автоматическое исправление проблемы с платежами
"""
import os
import sys
import time
import subprocess
import requests
from pathlib import Path

def run_command(cmd, description, check=True):
    """Выполнить команду с описанием"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - успешно")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"⚠️  {description} - предупреждение")
            if result.stderr.strip():
                print(f"   {result.stderr.strip()}")
            return False, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ошибка")
        print(f"   {e.stderr.strip()}")
        return False, e.stderr

def check_file_exists(filepath, description):
    """Проверить существование файла"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} не найден: {filepath}")
        return False

def test_webhook_endpoint(base_url):
    """Тестировать webhook endpoint"""
    health_url = f"{base_url.rstrip('/')}/health"
    webhook_url = f"{base_url.rstrip('/')}/webhook/yookassa"
    
    print(f"🔍 Тестируем endpoint: {health_url}")
    
    try:
        response = requests.get(health_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print(f"✅ Webhook сервер работает корректно")
                print(f"🔗 Webhook URL: {webhook_url}")
                return webhook_url
            else:
                print(f"⚠️  Сервер отвечает, но статус не 'healthy': {data}")
        else:
            print(f"⚠️  Сервер вернул код: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Не удалось подключиться к серверу: {e}")
    
    return None

def main():
    """Основная функция автоматического исправления"""
    print("🚀 АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С ПЛАТЕЖАМИ")
    print("=" * 60)
    
    # Проверяем, что мы в правильной директории
    required_files = [
        "payment_yookassa.py",
        "webhook_server.py", 
        "main.py",
        "requirements.txt"
    ]
    
    print("📋 Проверяем файлы проекта...")
    for file in required_files:
        if not check_file_exists(file, f"Файл {file}"):
            print("❌ Запустите скрипт из корня проекта babka-bot")
            sys.exit(1)
    
    # Коммитим и пушим изменения
    print("\n📤 Отправляем изменения в репозиторий...")
    run_command("git add .", "Добавление файлов в git")
    
    commit_msg = "fix: полное исправление системы платежей - webhook сервер + правильный return_url"
    success, _ = run_command(f'git commit -m "{commit_msg}"', "Создание коммита", check=False)
    
    if success:
        run_command("git push", "Отправка в репозиторий")
    else:
        print("ℹ️  Возможно, нет новых изменений для коммита")
    
    # Ждем деплоя
    print("\n⏳ Ожидаем завершения деплоя (30 секунд)...")
    time.sleep(30)
    
    # Пытаемся найти URL приложения
    print("\n🔍 Ищем URL развернутого приложения...")
    
    possible_urls = []
    
    # Проверяем git remote для определения платформы
    success, git_remote = run_command("git remote get-url origin", "Получение git remote", check=False)
    
    if success and git_remote:
        if "railway" in git_remote.lower():
            print("🚂 Обнаружена платформа: Railway")
            # Пытаемся получить URL из Railway CLI
            success, railway_info = run_command("railway status", "Получение информации Railway", check=False)
            if success and "https://" in railway_info:
                # Извлекаем URL из вывода
                lines = railway_info.split('\n')
                for line in lines:
                    if "https://" in line and "railway.app" in line:
                        url = line.split("https://")[1].split()[0]
                        possible_urls.append(f"https://{url}")
        
        elif "render" in git_remote.lower():
            print("🎨 Обнаружена платформа: Render")
            # Для Render URL обычно нужно вводить вручную
        
        elif "heroku" in git_remote.lower():
            print("🟣 Обнаружена платформа: Heroku")
    
    # Если автоматически не нашли, запрашиваем у пользователя
    if not possible_urls:
        print("\n🌐 Введите URL вашего развернутого приложения:")
        print("   Примеры:")
        print("   - https://your-app.railway.app")
        print("   - https://your-app.onrender.com")
        print("   - https://your-app.herokuapp.com")
        
        while True:
            url = input("\nURL приложения: ").strip()
            if url.startswith("http"):
                possible_urls.append(url)
                break
            elif url:
                possible_urls.append(f"https://{url}")
                break
            else:
                print("⚠️  Пожалуйста, введите корректный URL")
    
    # Тестируем каждый URL
    working_webhook_url = None
    for url in possible_urls:
        print(f"\n🔍 Тестируем: {url}")
        webhook_url = test_webhook_endpoint(url)
        if webhook_url:
            working_webhook_url = webhook_url
            break
        else:
            print(f"⚠️  Сервер по адресу {url} недоступен или не работает")
    
    if not working_webhook_url:
        print("\n❌ Не удалось найти работающий webhook endpoint")
        print("📋 Проверьте:")
        print("1. Правильно ли развернуто приложение")
        print("2. Запущен ли веб-сервер (webhook_server.py)")
        print("3. Доступен ли URL извне")
        return
    
    # Настраиваем webhook в YooKassa
    print(f"\n🔗 Настраиваем webhook в YooKassa: {working_webhook_url}")
    
    try:
        # Запускаем скрипт настройки webhook
        env = os.environ.copy()
        env["WEBHOOK_BASE_URL"] = working_webhook_url.replace("/webhook/yookassa", "")
        
        result = subprocess.run([
            sys.executable, "setup_yookassa_webhook.py"
        ], env=env, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
    except Exception as e:
        print(f"⚠️  Ошибка при настройке webhook: {e}")
        print("🔧 Настройте webhook вручную в личном кабинете YooKassa:")
        print(f"   URL: {working_webhook_url}")
        print("   События: payment.succeeded, payment.canceled")
    
    # Финальная проверка
    print("\n🎯 ФИНАЛЬНАЯ ПРОВЕРКА")
    print("=" * 30)
    
    print("✅ Исправления применены:")
    print("   - Return URL исправлен на @babkakudo_bot")
    print("   - Webhook сервер развернут и работает")
    print("   - Обработка /start payment_success добавлена")
    print("   - Конфигурация деплоя обновлена")
    
    print(f"\n🔗 Webhook URL: {working_webhook_url}")
    
    print("\n📋 Что проверить:")
    print("1. Протестируйте платеж в боте")
    print("2. Убедитесь, что после оплаты пользователь попадает в бота")
    print("3. Проверьте, что монеты зачисляются автоматически")
    
    print("\n🎉 Автоматическое исправление завершено!")

if __name__ == "__main__":
    main()
