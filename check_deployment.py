#!/usr/bin/env python3
"""
Проверка развернутого приложения и автоматическая настройка webhook
"""
import requests
import time
import json

def check_common_deployment_urls():
    """Проверить популярные URL для деплоя"""
    
    # Популярные варианты URL на основе имени репозитория
    possible_urls = [
        "https://babka-bot.railway.app",
        "https://babka-bot-production.railway.app", 
        "https://babka-bot.onrender.com",
        "https://babka-bot-production.onrender.com",
        "https://babka-ai-bot.railway.app",
        "https://babkakudo-bot.railway.app",
        "https://babka-bot.herokuapp.com",
        "https://babka-bot-webhook.onrender.com",
    ]
    
    print("🔍 Проверяем популярные URL развертывания...")
    
    working_urls = []
    
    for url in possible_urls:
        print(f"   Проверяем: {url}")
        try:
            health_url = f"{url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        print(f"   ✅ РАБОТАЕТ: {url}")
                        working_urls.append(url)
                    else:
                        print(f"   ⚠️  Отвечает, но статус не 'healthy': {url}")
                except:
                    print(f"   ⚠️  Отвечает, но не JSON: {url}")
            else:
                print(f"   ❌ Код {response.status_code}: {url}")
                
        except requests.exceptions.RequestException:
            print(f"   ❌ Недоступен: {url}")
    
    return working_urls

def setup_webhook_for_url(base_url):
    """Настроить webhook для конкретного URL"""
    webhook_url = f"{base_url}/webhook/yookassa"
    
    print(f"\n🔗 Настраиваем webhook: {webhook_url}")
    
    # Здесь должна быть логика настройки webhook в YooKassa
    # Но для этого нужны API ключи
    
    print("📋 Для настройки webhook в YooKassa:")
    print(f"   URL: {webhook_url}")
    print("   События: payment.succeeded, payment.canceled")
    
    return webhook_url

def main():
    """Основная функция"""
    print("🚀 ПРОВЕРКА РАЗВЕРТЫВАНИЯ И НАСТРОЙКА WEBHOOK")
    print("=" * 50)
    
    # Проверяем популярные URL
    working_urls = check_common_deployment_urls()
    
    if not working_urls:
        print("\n❌ Не найдено работающих развертываний")
        print("\n📋 Возможные причины:")
        print("1. Приложение еще не развернуто")
        print("2. Используется другой URL")
        print("3. Webhook сервер не запущен")
        print("4. Ошибки при деплое")
        
        print("\n🔧 Что делать:")
        print("1. Проверьте логи деплоя на Railway/Render/Heroku")
        print("2. Убедитесь, что webhook_server.py запускается")
        print("3. Проверьте переменные окружения")
        
        return
    
    print(f"\n✅ Найдено работающих развертываний: {len(working_urls)}")
    
    # Используем первый работающий URL
    main_url = working_urls[0]
    webhook_url = setup_webhook_for_url(main_url)
    
    print(f"\n🎯 РЕЗУЛЬТАТ")
    print("=" * 20)
    print(f"✅ Рабочий URL: {main_url}")
    print(f"🔗 Webhook URL: {webhook_url}")
    
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Войдите в личный кабинет YooKassa")
    print("2. Перейдите в раздел 'Настройки' → 'Webhook'и'")
    print(f"3. Добавьте webhook с URL: {webhook_url}")
    print("4. Выберите события: payment.succeeded, payment.canceled")
    print("5. Сохраните настройки")
    print("6. Протестируйте платеж в боте")
    
    print(f"\n🔍 Для проверки работы откройте: {main_url}/health")

if __name__ == "__main__":
    main()
