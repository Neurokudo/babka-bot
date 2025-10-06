#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений кнопки Тарифы
"""
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_pricing_functions():
    """Тестируем функции pricing"""
    print("=== Тестирование функций pricing ===")
    
    try:
        from app.services.pricing import get_available_tariffs, format_plans_list
        
        # Тест get_available_tariffs
        tariffs = get_available_tariffs()
        print(f"✅ get_available_tariffs() вернул {len(tariffs)} тарифов")
        print(f"   Тип: {type(tariffs)}")
        
        for tariff in tariffs:
            print(f"   - {tariff['name']}: {tariff['title']} — {tariff['price_rub']:,} ₽")
        
        # Тест format_plans_list
        plans_text = format_plans_list()
        print(f"✅ format_plans_list() вернул текст длиной {len(plans_text)} символов")
        print("   Первые 200 символов:")
        print(f"   {plans_text[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в функциях pricing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_billing_functions():
    """Тестируем функции биллинга"""
    print("\n=== Тестирование функций биллинга ===")
    
    try:
        from app.db import db_subscriptions as db
        
        # Тест get_user_balance
        test_user_id = 5015100177
        balance = db.get_user_balance(test_user_id)
        print(f"✅ get_user_balance({test_user_id}) = {balance}")
        
        # Тест charge_feature (небольшая сумма)
        success = db.charge_feature(test_user_id, "test_feature", 1, note="test_charge")
        print(f"✅ charge_feature() = {success}")
        
        # Восстанавливаем баланс
        if success:
            db.update_user_balance(test_user_id, 1, note="restore_after_test")
            print("✅ Баланс восстановлен")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в функциях биллинга: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_old_queries_redirect():
    """Тестируем перенаправление старых запросов"""
    print("\n=== Тестирование перенаправления старых запросов ===")
    
    try:
        from app.db.queries import charge_feature
        
        # Тест перенаправления
        test_user_id = 5015100177
        success = charge_feature(test_user_id, "test_redirect", 1, note="test_redirect")
        print(f"✅ queries.charge_feature() перенаправлен = {success}")
        
        # Восстанавливаем баланс
        if success:
            from app.db import db_subscriptions as db
            db.update_user_balance(test_user_id, 1, note="restore_after_redirect_test")
            print("✅ Баланс восстановлен после теста перенаправления")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в перенаправлении: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Тестирование исправлений кнопки Тарифы\n")
    
    results = []
    results.append(test_pricing_functions())
    results.append(test_billing_functions())
    results.append(test_old_queries_redirect())
    
    print(f"\n=== Результаты тестирования ===")
    print(f"✅ Успешных тестов: {sum(results)}")
    print(f"❌ Неудачных тестов: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 Все тесты прошли успешно!")
        return 0
    else:
        print("💥 Некоторые тесты не прошли!")
        return 1

if __name__ == "__main__":
    exit(main())
