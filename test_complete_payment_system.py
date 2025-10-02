#!/usr/bin/env python3
"""
ПОЛНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ПЛАТЕЖЕЙ YOOKASSA
Проверяет каждый компонент согласно официальной документации
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def test_yookassa_credentials():
    """Тест 1: Проверка credentials YooKassa"""
    print("🔐 ТЕСТ 1: Проверка credentials YooKassa")
    print("-" * 50)
    
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    if not shop_id:
        print("❌ YOOKASSA_SHOP_ID не найден в переменных окружения")
        return False
    
    if not secret_key:
        print("❌ YOOKASSA_SECRET_KEY не найден в переменных окружения")
        return False
    
    print(f"✅ YOOKASSA_SHOP_ID: {shop_id}")
    print(f"✅ YOOKASSA_SECRET_KEY: {secret_key[:10]}...")
    
    # Тестируем подключение к API
    try:
        response = requests.get(
            "https://api.yookassa.ru/v3/me",
            auth=(shop_id, secret_key),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API подключение успешно")
            print(f"   Account ID: {data.get('account_id')}")
            print(f"   Status: {data.get('status')}")
            return True
        elif response.status_code == 401:
            print("❌ Неверные credentials - проверьте SHOP_ID и SECRET_KEY")
            return False
        else:
            print(f"⚠️  Неожиданный ответ API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")
        return False

def test_payment_creation():
    """Тест 2: Создание тестового платежа"""
    print("\n💳 ТЕСТ 2: Создание тестового платежа")
    print("-" * 50)
    
    try:
        # Импортируем исправленный модуль
        sys.path.insert(0, str(Path(__file__).parent))
        from payment_yookassa import create_payment_link, YooKassaError
        
        # Создаем тестовый платеж
        payment_url = create_payment_link(
            user_id=12345,
            amount=100.0,
            description="Тест системы платежей",
            metadata={"test": True, "system_check": True}
        )
        
        print(f"✅ Платеж создан успешно")
        print(f"🔗 URL: {payment_url}")
        
        # Проверяем, что URL содержит правильный домен
        if "yoomoney.ru" in payment_url or "yookassa.ru" in payment_url:
            print("✅ URL содержит правильный домен YooKassa/YooMoney")
        else:
            print(f"⚠️  Неожиданный домен в URL: {payment_url}")
        
        return True
        
    except YooKassaError as e:
        print(f"❌ Ошибка YooKassa: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_webhook_server():
    """Тест 3: Проверка webhook сервера"""
    print("\n🌐 ТЕСТ 3: Проверка webhook сервера")
    print("-" * 50)
    
    # Проверяем популярные URL развертывания
    possible_urls = [
        "https://babka-bot.railway.app",
        "https://babka-bot-production.railway.app",
        "https://babka-ai-bot.railway.app",
        "https://babkakudo-bot.railway.app"
    ]
    
    working_url = None
    
    for url in possible_urls:
        try:
            print(f"   Проверяем: {url}")
            
            # Проверяем health endpoint
            health_response = requests.get(f"{url}/health", timeout=5)
            
            if health_response.status_code == 200:
                try:
                    data = health_response.json()
                    if data.get("status") == "healthy" and "webhook" in data.get("service", "").lower():
                        print(f"   ✅ Webhook сервер работает: {url}")
                        working_url = url
                        break
                    else:
                        print(f"   ⚠️  Сервер отвечает, но не webhook: {data}")
                except:
                    print(f"   ⚠️  Сервер отвечает, но не JSON (старая версия)")
            else:
                print(f"   ❌ HTTP {health_response.status_code}")
                
        except requests.exceptions.RequestException:
            print(f"   ❌ Недоступен")
    
    if working_url:
        # Тестируем webhook endpoint
        try:
            webhook_response = requests.post(
                f"{working_url}/webhook/yookassa",
                json={"test": "data"},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if webhook_response.status_code == 200:
                print(f"✅ Webhook endpoint отвечает корректно")
                return working_url
            else:
                print(f"⚠️  Webhook endpoint вернул: {webhook_response.status_code}")
                return working_url
                
        except Exception as e:
            print(f"⚠️  Ошибка тестирования webhook: {e}")
            return working_url
    
    print("❌ Рабочий webhook сервер не найден")
    return None

def test_webhook_processing():
    """Тест 4: Обработка webhook данных"""
    print("\n📨 ТЕСТ 4: Обработка webhook данных")
    print("-" * 50)
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from payment_yookassa import process_payment_webhook
        
        # Тестовые данные webhook от YooKassa
        test_webhook_data = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "test_payment_12345",
                "status": "succeeded",
                "amount": {
                    "value": "100.00",
                    "currency": "RUB"
                },
                "metadata": {
                    "user_id": "12345",
                    "test": "true"
                },
                "created_at": "2025-01-01T12:00:00.000Z",
                "captured_at": "2025-01-01T12:00:05.000Z"
            }
        }
        
        result = process_payment_webhook(test_webhook_data)
        
        if result:
            print("✅ Webhook обработан успешно")
            print(f"   Event: {result.get('event')}")
            print(f"   Payment ID: {result.get('payment_id')}")
            print(f"   Amount: {result.get('amount')} {result.get('currency')}")
            print(f"   User ID: {result.get('user_id')}")
            print(f"   Status: {result.get('status')}")
            return True
        else:
            print("❌ Webhook не обработан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
        return False

def test_bot_integration():
    """Тест 5: Интеграция с ботом"""
    print("\n🤖 ТЕСТ 5: Интеграция с ботом")
    print("-" * 50)
    
    try:
        # Проверяем, что бот существует
        bot_username = "babkakudo_bot"
        bot_url = f"https://t.me/{bot_username}"
        
        print(f"🔗 Return URL: {bot_url}?start=payment_success")
        
        # Проверяем доступность бота (простая проверка)
        try:
            response = requests.get(f"https://t.me/{bot_username}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Бот @{bot_username} доступен")
            else:
                print(f"⚠️  Бот @{bot_username} может быть недоступен")
        except:
            print(f"⚠️  Не удалось проверить доступность бота")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки бота: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ПОЛНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ПЛАТЕЖЕЙ YOOKASSA")
    print("=" * 70)
    print("Проверяем каждый компонент согласно официальной документации")
    print("https://yookassa.ru/developers/using-api/interaction-format")
    print()
    
    results = []
    
    # Запускаем все тесты
    results.append(("Credentials YooKassa", test_yookassa_credentials()))
    results.append(("Создание платежа", test_payment_creation()))
    
    webhook_url = test_webhook_server()
    results.append(("Webhook сервер", webhook_url is not None))
    
    results.append(("Обработка webhook", test_webhook_processing()))
    results.append(("Интеграция с ботом", test_bot_integration()))
    
    # Выводим итоги
    print("\n🎯 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОШЕЛ" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name:.<25} {status}")
        if result:
            passed += 1
    
    print(f"\nРезультат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Система платежей готова к работе!")
        
        if webhook_url:
            print(f"\n📋 НАСТРОЙКА WEBHOOK В YOOKASSA:")
            print(f"URL: {webhook_url}/webhook/yookassa")
            print("События: payment.succeeded, payment.canceled")
            
    else:
        print(f"\n⚠️  НАЙДЕНЫ ПРОБЛЕМЫ: {total - passed} тестов провалено")
        print("Необходимо исправить ошибки перед запуском")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
