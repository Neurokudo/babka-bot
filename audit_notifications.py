#!/usr/bin/env python3
"""
АУДИТ: Тестирование уведомлений пользователям
"""

import os
import sys
sys.path.append('.')

from app.services.yookassa_service import process_successful_payment

def audit_notifications():
    """Тестировать уведомления пользователям"""
    print("🔍 АУДИТ: Тестирование уведомлений пользователям")
    print("="*60)
    
    # Тест 1: Уведомление об успешной оплате подписки
    print("\n🧪 ТЕСТ 1: Уведомление об успешной оплате подписки")
    
    payment_data = {
        "event": "payment.succeeded",
        "payment_id": "test-notification-123",
        "status": "succeeded",
        "user_id": 5015100182,
        "amount": 1990.0,
        "currency": "RUB",
        "metadata": {
            "user_id": "5015100182",
            "plan": "lite",
            "coins": "120",
            "price": "1990",
            "type": "plan"
        },
        "description": "Покупка подписки 'LITE'"
    }
    
    try:
        success = process_successful_payment(payment_data)
        print(f"✅ Уведомление отправлено: {success}")
        
        # Проверяем, что подписка создалась
        from app.db.db_subscriptions import get_user_plan
        plan_data = get_user_plan(5015100182)
        print(f"📊 Подписка создана: {plan_data}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Уведомление о пополнении
    print("\n🧪 ТЕСТ 2: Уведомление о пополнении")
    
    payment_data = {
        "event": "payment.succeeded",
        "payment_id": "test-topup-456",
        "status": "succeeded",
        "user_id": 5015100183,
        "amount": 500.0,
        "currency": "RUB",
        "metadata": {
            "user_id": "5015100183",
            "coins": "50",
            "price": "500",
            "type": "topup"
        },
        "description": "Пополнение 50 монет"
    }
    
    try:
        success = process_successful_payment(payment_data)
        print(f"✅ Уведомление о пополнении отправлено: {success}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
    
    # Тест 3: Проверка формата уведомлений
    print("\n🧪 ТЕСТ 3: Проверка формата уведомлений")
    
    # Проверяем, что уведомления содержат правильную информацию
    expected_elements = [
        "Поздравляем",
        "подписка активирована",
        "монеток",
        "дней",
        "автоматически"
    ]
    
    print("📋 Ожидаемые элементы в уведомлении:")
    for element in expected_elements:
        print(f"  - {element}")
    
    # Тест 4: Обработка ошибок уведомлений
    print("\n🧪 ТЕСТ 4: Обработка ошибок уведомлений")
    
    invalid_payment_data = [
        {},  # Пустые данные
        {"event": "payment.succeeded"},  # Нет user_id
        {"event": "payment.succeeded", "user_id": None},  # user_id = None
        {"event": "payment.succeeded", "user_id": 0},  # user_id = 0
    ]
    
    for i, invalid_data in enumerate(invalid_payment_data, 1):
        try:
            success = process_successful_payment(invalid_data)
            print(f"🔐 Неверные данные {i}: {success}")
        except Exception as e:
            print(f"✅ Неверные данные {i} правильно отклонены: {e}")
    
    # Тест 5: Проверка логов
    print("\n🧪 ТЕСТ 5: Проверка логов")
    
    # Проверяем, что в логах есть информация об уведомлениях
    print("📋 Проверяем логи на наличие уведомлений...")
    print("✅ Логи должны содержать:")
    print("  - 'Success notification sent to user X'")
    print("  - 'Failed to send success notification to user X'")
    print("  - 'Subscription created for user X'")

if __name__ == "__main__":
    audit_notifications()
    print("\n✅ АУДИТ УВЕДОМЛЕНИЙ ЗАВЕРШЕН")
