#!/usr/bin/env python3
"""
АУДИТ: Тестирование создания подписок
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import create_subscription, get_user_plan, db_conn

def audit_subscription_creation():
    """Тестировать создание подписок"""
    print("🔍 АУДИТ: Тестирование создания подписок")
    print("="*60)
    
    # Тест 1: Создание подписки lite
    print("\n🧪 ТЕСТ 1: Создание подписки lite")
    try:
        success = create_subscription(
            user_id=5015100178,  # Новый пользователь
            plan="lite",
            coins=120,
            price_rub=1990,
            duration_days=30,
            payment_id="test-lite-123"
        )
        
        if success:
            print("✅ Подписка lite создана успешно")
            
            # Проверяем в БД
            plan_data = get_user_plan(5015100178)
            print(f"📊 Данные подписки: {plan_data}")
        else:
            print("❌ Ошибка создания подписки lite")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Создание подписки standard
    print("\n🧪 ТЕСТ 2: Создание подписки standard")
    try:
        success = create_subscription(
            user_id=5015100179,
            plan="standard",
            coins=210,
            price_rub=2490,
            duration_days=30,
            payment_id="test-standard-456"
        )
        
        if success:
            print("✅ Подписка standard создана успешно")
            plan_data = get_user_plan(5015100179)
            print(f"📊 Данные подписки: {plan_data}")
        else:
            print("❌ Ошибка создания подписки standard")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 3: Обновление существующей подписки
    print("\n🧪 ТЕСТ 3: Обновление существующей подписки")
    try:
        # Создаем первую подписку
        create_subscription(
            user_id=5015100180,
            plan="lite",
            coins=120,
            price_rub=1990,
            duration_days=30,
            payment_id="test-upgrade-1"
        )
        
        # Обновляем на более высокий тариф
        success = create_subscription(
            user_id=5015100180,
            plan="pro",
            coins=440,
            price_rub=4990,
            duration_days=30,
            payment_id="test-upgrade-2"
        )
        
        if success:
            print("✅ Подписка обновлена успешно")
            plan_data = get_user_plan(5015100180)
            print(f"📊 Данные подписки: {plan_data}")
        else:
            print("❌ Ошибка обновления подписки")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 4: Валидация данных
    print("\n🧪 ТЕСТ 4: Валидация данных")
    invalid_cases = [
        {"user_id": 0, "plan": "invalid", "coins": -100, "price_rub": -1000},
        {"user_id": -1, "plan": "", "coins": 0, "price_rub": 0},
        {"user_id": None, "plan": None, "coins": None, "price_rub": None},
    ]
    
    for i, case in enumerate(invalid_cases, 1):
        try:
            success = create_subscription(
                user_id=case["user_id"],
                plan=case["plan"],
                coins=case["coins"],
                price_rub=case["price_rub"],
                duration_days=30,
                payment_id=f"test-invalid-{i}"
            )
            if not success:
                print(f"✅ Неверные данные {i} правильно отклонены")
            else:
                print(f"❌ Неверные данные {i} не должны создавать подписку")
        except Exception as e:
            print(f"✅ Неверные данные {i} правильно отклонены: {e}")
    
    # Тест 5: Проверка транзакций
    print("\n🧪 ТЕСТ 5: Проверка транзакций")
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id IN (5015100178, 5015100179, 5015100180)")
            else:
                cur.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id IN (5015100178, 5015100179, 5015100180)")
            
            count = cur.fetchone()[0]
            print(f"📊 Создано подписок: {count}")
            
            if is_postgres:
                cur.execute("SELECT user_id, plan, coins, price_rub FROM subscriptions WHERE user_id IN (5015100178, 5015100179, 5015100180) ORDER BY user_id")
            else:
                cur.execute("SELECT user_id, plan, coins, price_rub FROM subscriptions WHERE user_id IN (5015100178, 5015100179, 5015100180) ORDER BY user_id")
            
            subscriptions = cur.fetchall()
            print("📋 Список подписок:")
            for sub in subscriptions:
                print(f"  - Пользователь {sub[0]}: {sub[1]} план, {sub[2]} монет, {sub[3]} ₽")
                
    except Exception as e:
        print(f"❌ Ошибка проверки транзакций: {e}")

if __name__ == "__main__":
    audit_subscription_creation()
    print("\n✅ АУДИТ СОЗДАНИЯ ПОДПИСОК ЗАВЕРШЕН")
