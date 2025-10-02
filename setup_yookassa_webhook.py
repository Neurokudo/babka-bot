#!/usr/bin/env python3
"""
Автоматическая настройка webhook в YooKassa
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def setup_webhook(webhook_url):
    """Настройка webhook в YooKassa"""
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    if not shop_id or not secret_key:
        print("❌ Не найдены YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY")
        return False
    
    # Создаем webhook
    webhook_data = {
        "event": "payment.succeeded",
        "url": webhook_url
    }
    
    try:
        response = requests.post(
            "https://api.yookassa.ru/v3/webhooks",
            json=webhook_data,
            auth=(shop_id, secret_key),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Webhook успешно создан: {webhook_url}")
            print(f"   ID: {response.json().get('id')}")
            return True
        else:
            print(f"❌ Ошибка создания webhook: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при настройке webhook: {e}")
        return False

def get_existing_webhooks():
    """Получить список существующих webhook'ов"""
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    if not shop_id or not secret_key:
        return []
    
    try:
        response = requests.get(
            "https://api.yookassa.ru/v3/webhooks",
            auth=(shop_id, secret_key)
        )
        
        if response.status_code == 200:
            webhooks = response.json().get("items", [])
            print(f"📋 Найдено webhook'ов: {len(webhooks)}")
            for webhook in webhooks:
                print(f"   - {webhook.get('event')}: {webhook.get('url')}")
            return webhooks
        else:
            print(f"⚠️  Не удалось получить список webhook'ов: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️  Ошибка при получении webhook'ов: {e}")
        return []

def main():
    """Основная функция"""
    print("🔗 Настройка webhook для YooKassa")
    print("=" * 40)
    
    # Пытаемся определить URL приложения
    possible_urls = []
    
    # Проверяем переменные окружения
    railway_url = os.getenv("RAILWAY_STATIC_URL")
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    custom_url = os.getenv("WEBHOOK_BASE_URL")
    
    if railway_url:
        possible_urls.append(f"https://{railway_url}")
    if render_url:
        possible_urls.append(render_url)
    if custom_url:
        possible_urls.append(custom_url)
    
    # Если URL не найден, запрашиваем у пользователя
    if not possible_urls:
        print("🌐 Введите URL вашего развернутого приложения:")
        print("   Примеры:")
        print("   - https://your-app.railway.app")
        print("   - https://your-app.onrender.com")
        print("   - https://your-domain.com")
        
        base_url = input("URL: ").strip()
        if base_url:
            possible_urls.append(base_url)
    
    if not possible_urls:
        print("❌ URL приложения не указан")
        return
    
    # Получаем существующие webhook'и
    print("\n📋 Проверяем существующие webhook'и...")
    existing_webhooks = get_existing_webhooks()
    
    # Настраиваем webhook для каждого URL
    for base_url in possible_urls:
        webhook_url = f"{base_url.rstrip('/')}/webhook/yookassa"
        
        print(f"\n🔗 Настраиваем webhook: {webhook_url}")
        
        # Проверяем, не существует ли уже такой webhook
        webhook_exists = any(
            webhook.get("url") == webhook_url 
            for webhook in existing_webhooks
        )
        
        if webhook_exists:
            print(f"ℹ️  Webhook уже существует: {webhook_url}")
            continue
        
        # Проверяем доступность endpoint'а
        try:
            health_url = f"{base_url.rstrip('/')}/health"
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Сервер доступен: {health_url}")
                
                # Настраиваем webhook
                if setup_webhook(webhook_url):
                    print(f"🎉 Webhook успешно настроен!")
                    break
                else:
                    print(f"❌ Не удалось настроить webhook")
            else:
                print(f"⚠️  Сервер недоступен: {health_url} (код: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Не удалось проверить доступность сервера: {e}")
    
    print("\n✅ Настройка завершена!")
    print("\n📋 Что дальше:")
    print("1. Убедитесь, что ваше приложение развернуто и работает")
    print("2. Проверьте логи приложения на наличие ошибок")
    print("3. Протестируйте платеж в боте")

if __name__ == "__main__":
    main()
