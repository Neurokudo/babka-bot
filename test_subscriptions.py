#!/usr/bin/env python3
"""
Тест интеграции модуля подписок
"""

import os
import sys
from dotenv import load_dotenv

def test_subscriptions_integration():
    """Тестирование интеграции модуля подписок"""
    load_dotenv()
    
    print("🧪 Тестирование модуля подписок...")
    
    try:
        # Импортируем модуль
        from app.db import db_subscriptions as db
        print("✅ Модуль db_subscriptions импортирован")
        
        # Тестируем создание пользователя
        test_user_id = 999999
        db.create_or_update_user(test_user_id, "test_user", "Test", "User")
        print(f"✅ Пользователь {test_user_id} создан/обновлен")
        
        # Тестируем получение баланса
        balance = db.get_user_balance(test_user_id)
        print(f"✅ Баланс пользователя: {balance} монет")
        
        # Тестируем создание подписки
        db.create_subscription(
            user_id=test_user_id,
            plan="lite",
            coins=120,
            price_rub=1990,
            duration_days=30,
            payment_id="test_payment_123"
        )
        print("✅ Подписка создана")
        
        # Проверяем баланс после подписки
        new_balance = db.get_user_balance(test_user_id)
        print(f"✅ Баланс после подписки: {new_balance} монет")
        
        # Тестируем списание монет
        success = db.charge_feature(test_user_id, "transform", 1, "Test charge")
        print(f"✅ Списание монет: {'успешно' if success else 'неудачно'}")
        
        # Проверяем баланс после списания
        final_balance = db.get_user_balance(test_user_id)
        print(f"✅ Баланс после списания: {final_balance} монет")
        
        # Тестируем получение информации о плане
        plan_info = db.get_user_plan(test_user_id)
        print(f"✅ Информация о плане: {plan_info}")
        
        # Тестируем проверку просроченных подписок
        db.check_expired_subscriptions()
        print("✅ Проверка просроченных подписок выполнена")
        
        print("\n🎉 Все тесты прошли успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pricing_integration():
    """Тестирование интеграции с модулем pricing"""
    print("\n🧪 Тестирование интеграции с pricing...")
    
    try:
        from app.services.pricing import get_tariff_by_name, feature_cost_coins
        
        # Тестируем получение тарифа
        lite_tariff = get_tariff_by_name("lite")
        if lite_tariff:
            print(f"✅ Тариф lite: {lite_tariff['title']}, {lite_tariff['coins']} монет")
        
        # Тестируем получение стоимости функций
        transform_cost = feature_cost_coins("transform")
        print(f"✅ Стоимость transform: {transform_cost} монет")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании pricing: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов интеграции модуля подписок\n")
    
    # Тестируем pricing
    pricing_ok = test_pricing_integration()
    
    # Тестируем subscriptions
    subscriptions_ok = test_subscriptions_integration()
    
    if pricing_ok and subscriptions_ok:
        print("\n✅ Все тесты прошли успешно!")
        sys.exit(0)
    else:
        print("\n❌ Некоторые тесты не прошли")
        sys.exit(1)
