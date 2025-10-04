#!/usr/bin/env python3
"""
АУДИТ: Тестирование создания платежей YooKassa
"""

import os
import sys
sys.path.append('.')

# Устанавливаем переменные окружения для тестирования
os.environ['YOOKASSA_SHOP_ID'] = '1176639'
os.environ['YOOKASSA_SECRET_KEY'] = 'live_PDdv14wxc9W36rSeeE8j7c4tsnHw-N-Exnra0lMk2HU'

from app.services.yookassa_service import create_payment, create_topup_payment, check_payment_status, init_yookassa

def audit_yookassa_payments():
    """Тестировать создание платежей YooKassa"""
    print("🔍 АУДИТ: Тестирование платежей YooKassa")
    print("="*60)
    
    # Тест 1: Инициализация YooKassa
    print("\n🧪 ТЕСТ 1: Инициализация YooKassa")
    try:
        init_result = init_yookassa()
        if init_result:
            print("✅ YooKassa инициализирован успешно")
        else:
            print("❌ Ошибка инициализации YooKassa")
            return False
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return False
    
    # Тест 2: Создание платежа за подписку
    print("\n🧪 ТЕСТ 2: Создание платежа за подписку")
    try:
        user_id = 5015100177
        plan = "standard"
        price_rub = 2490
        coins = 210
        
        payment_url, payment_id = create_payment(
            user_id=user_id,
            plan=plan,
            price_rub=price_rub,
            coins=coins,
            username="test_user"
        )
        
        print(f"✅ Платеж создан успешно")
        print(f"🆔 ID платежа: {payment_id}")
        print(f"🔗 URL: {payment_url}")
        print(f"💰 Сумма: {price_rub} ₽")
        print(f"🎟️ Монет: {coins}")
        
        # Проверяем статус платежа
        print("\n🔍 Проверка статуса платежа...")
        status = check_payment_status(payment_id)
        print(f"📊 Статус: {status.get('status', 'unknown')}")
        print(f"💰 Сумма: {status.get('amount', 0)} {status.get('currency', 'RUB')}")
        print(f"🏷️ Метаданные: {status.get('metadata', {})}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания платежа: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Тест 3: Создание платежа за пополнение
    print("\n🧪 ТЕСТ 3: Создание платежа за пополнение")
    try:
        user_id = 5015100177
        coins = 50
        price_rub = 500
        
        payment_url, payment_id = create_topup_payment(
            user_id=user_id,
            coins=coins,
            price_rub=price_rub,
            username="test_user"
        )
        
        print(f"✅ Платеж пополнения создан успешно")
        print(f"🆔 ID платежа: {payment_id}")
        print(f"🔗 URL: {payment_url}")
        print(f"💰 Сумма: {price_rub} ₽")
        print(f"🎟️ Монет: {coins}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания платежа пополнения: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_payment_validation():
    """Тестировать валидацию платежей"""
    print("\n🧪 ТЕСТ 4: Валидация платежей")
    
    # Тест с неверными данными
    test_cases = [
        {"user_id": 0, "plan": "invalid", "price_rub": -100, "coins": -50},
        {"user_id": -1, "plan": "", "price_rub": 0, "coins": 0},
        {"user_id": None, "plan": None, "price_rub": None, "coins": None},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Тест {i}: {test_case}")
        try:
            payment_url, payment_id = create_payment(
                user_id=test_case["user_id"],
                plan=test_case["plan"],
                price_rub=test_case["price_rub"],
                coins=test_case["coins"],
                username="test_user"
            )
            print(f"  ❌ Платеж создан с неверными данными! ID: {payment_id}")
        except Exception as e:
            print(f"  ✅ Валидация работает: {e}")

if __name__ == "__main__":
    success = audit_yookassa_payments()
    test_payment_validation()
    
    if success:
        print("\n✅ АУДИТ ПЛАТЕЖЕЙ ЗАВЕРШЕН УСПЕШНО")
    else:
        print("\n❌ АУДИТ ПЛАТЕЖЕЙ ЗАВЕРШЕН С ОШИБКАМИ")
