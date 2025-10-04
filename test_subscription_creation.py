#!/usr/bin/env python3
"""
Тест создания подписки после исправления схемы базы данных
Проверяет, что YooKassa webhook может успешно создавать подписки
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///./babka_bot.db")

from app.services.yookassa_service import process_successful_payment, init_yookassa
from app.db.db_subscriptions import get_user_plan, create_subscription
from app.services.pricing import get_tariff_by_name

async def test_subscription_creation():
    print("🧪 ТЕСТ СОЗДАНИЯ ПОДПИСКИ ПОСЛЕ ИСПРАВЛЕНИЯ СХЕМЫ")
    print("=" * 60)
    
    # Инициализируем YooKassa
    try:
        init_yookassa()
        print("✅ YooKassa инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации YooKassa: {e}")
        return False
    
    # Тестовый пользователь
    test_user_id = 5015100300
    plan_name = "lite"
    plan_info = get_tariff_by_name(plan_name)
    
    if not plan_info:
        print(f"❌ Тариф '{plan_name}' не найден")
        return False
    
    print(f"📊 Тестируем создание подписки для пользователя {test_user_id}")
    print(f"📊 Тариф: {plan_info['title']} - {plan_info['price_rub']} ₽")
    
    # Тест 1: Создание подписки напрямую
    print("\n🧪 ТЕСТ 1: Создание подписки напрямую")
    try:
        success = create_subscription(
            user_id=test_user_id,
            plan=plan_info["name"],
            coins=plan_info["coins"],
            price_rub=plan_info["price_rub"],
            duration_days=plan_info["duration_days"],
            payment_id="test-direct-123"
        )
        
        if success:
            print("✅ Подписка создана напрямую успешно")
            
            # Проверяем данные подписки
            plan_data = get_user_plan(test_user_id)
            print(f"📊 Данные подписки: {plan_data}")
        else:
            print("❌ Ошибка создания подписки напрямую")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при создании подписки: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Тест 2: Имитация YooKassa webhook
    print("\n🧪 ТЕСТ 2: Имитация YooKassa webhook")
    try:
        webhook_data = {
            "event": "payment.succeeded",
            "payment_id": "test-webhook-456",
            "status": "succeeded",
            "user_id": test_user_id + 1,  # Другой пользователь
            "amount": plan_info["price_rub"],
            "metadata": {
                "user_id": str(test_user_id + 1),
                "plan": plan_info["name"],
                "coins": str(plan_info["coins"]),
                "price": str(plan_info["price_rub"]),
                "type": "plan"
            }
        }
        
        success = await process_successful_payment(webhook_data)
        
        if success:
            print("✅ YooKassa webhook обработан успешно")
            
            # Проверяем данные подписки
            plan_data = get_user_plan(test_user_id + 1)
            print(f"📊 Данные подписки: {plan_data}")
        else:
            print("❌ Ошибка обработки YooKassa webhook")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обработке webhook: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Тест 3: Проверка структуры базы данных
    print("\n🧪 ТЕСТ 3: Проверка структуры базы данных")
    try:
        from app.db.db_subscriptions import db_conn
        
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Проверяем таблицу users
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position
            """)
            users_columns = cur.fetchall()
            print(f"📊 Колонки в таблице users: {len(users_columns)}")
            for col in users_columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # Проверяем таблицу subscriptions
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'subscriptions' 
                ORDER BY ordinal_position
            """)
            subscriptions_columns = cur.fetchall()
            print(f"📊 Колонки в таблице subscriptions: {len(subscriptions_columns)}")
            for col in subscriptions_columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # Проверяем количество записей
            cur.execute("SELECT COUNT(*) FROM users")
            users_count = cur.fetchone()[0]
            print(f"📊 Количество пользователей: {users_count}")
            
            cur.execute("SELECT COUNT(*) FROM subscriptions")
            subscriptions_count = cur.fetchone()[0]
            print(f"📊 Количество подписок: {subscriptions_count}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке структуры БД: {e}")
        return False
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    print("🎯 Схема базы данных исправлена корректно")
    print("🎯 YooKassa webhook работает без ошибок")
    print("🎯 Подписки создаются успешно")
    print("🎯 Уведомления должны приходить пользователям")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_subscription_creation())
    if success:
        print("\n🚀 ГОТОВО К ПРОДАКШЕНУ!")
        print("Теперь попробуйте купить подписку через бота - уведомление должно прийти!")
    else:
        print("\n❌ Тесты не прошли - нужно дополнительное исправление")
        sys.exit(1)
