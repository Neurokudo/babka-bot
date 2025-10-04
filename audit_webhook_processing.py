#!/usr/bin/env python3
"""
АУДИТ: Тестирование webhook обработки платежей
"""

import os
import sys
sys.path.append('.')

from app.services.yookassa_service import process_payment_webhook, process_successful_payment

def audit_webhook_processing():
    """Тестировать webhook обработку платежей"""
    print("🔍 АУДИТ: Тестирование webhook обработки")
    print("="*60)
    
    # Тест 1: Успешный платеж за подписку
    print("\n🧪 ТЕСТ 1: Успешный платеж за подписку")
    webhook_data = {
        "event": "payment.succeeded",
        "object": {
            "id": "test-payment-123",
            "status": "succeeded",
            "amount": {"value": "1990.00", "currency": "RUB"},
            "description": "Покупка подписки 'LITE'",
            "metadata": {
                "user_id": "5015100177",
                "plan": "lite",
                "coins": "120",
                "price": "1990",
                "type": "plan"
            }
        }
    }
    
    try:
        # Обрабатываем webhook
        payment_data = process_payment_webhook(webhook_data)
        if payment_data:
            print(f"✅ Webhook обработан: {payment_data}")
            
            # Обрабатываем успешный платеж
            success = process_successful_payment(payment_data)
            print(f"✅ Платеж обработан: {success}")
        else:
            print("❌ Webhook не обработан")
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Платеж за пополнение
    print("\n🧪 ТЕСТ 2: Платеж за пополнение")
    webhook_data = {
        "event": "payment.succeeded",
        "object": {
            "id": "test-topup-456",
            "status": "succeeded",
            "amount": {"value": "500.00", "currency": "RUB"},
            "description": "Пополнение 50 монет",
            "metadata": {
                "user_id": "5015100177",
                "coins": "50",
                "price": "500",
                "type": "topup"
            }
        }
    }
    
    try:
        payment_data = process_payment_webhook(webhook_data)
        if payment_data:
            print(f"✅ Webhook обработан: {payment_data}")
            success = process_successful_payment(payment_data)
            print(f"✅ Платеж обработан: {success}")
        else:
            print("❌ Webhook не обработан")
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
    
    # Тест 3: Неподдерживаемые события
    print("\n🧪 ТЕСТ 3: Неподдерживаемые события")
    unsupported_events = [
        {"event": "payment.canceled", "object": {"id": "test-1"}},
        {"event": "payment.waiting_for_capture", "object": {"id": "test-2"}},
        {"event": "refund.succeeded", "object": {"id": "test-3"}},
    ]
    
    for event_data in unsupported_events:
        try:
            result = process_payment_webhook(event_data)
            if result is None:
                print(f"✅ Событие {event_data['event']} правильно проигнорировано")
            else:
                print(f"❌ Событие {event_data['event']} не должно обрабатываться")
        except Exception as e:
            print(f"❌ Ошибка при обработке {event_data['event']}: {e}")
    
    # Тест 4: Неверные данные
    print("\n🧪 ТЕСТ 4: Неверные данные")
    invalid_data = [
        {},  # Пустые данные
        {"event": "payment.succeeded"},  # Нет object
        {"event": "payment.succeeded", "object": {}},  # Пустой object
        {"event": "payment.succeeded", "object": {"id": "test", "metadata": {}}},  # Нет user_id
    ]
    
    for i, invalid in enumerate(invalid_data, 1):
        try:
            result = process_payment_webhook(invalid)
            if result is None:
                print(f"✅ Неверные данные {i} правильно проигнорированы")
            else:
                print(f"❌ Неверные данные {i} не должны обрабатываться")
        except Exception as e:
            print(f"✅ Неверные данные {i} правильно отклонены: {e}")

if __name__ == "__main__":
    audit_webhook_processing()
    print("\n✅ АУДИТ WEBHOOK ЗАВЕРШЕН")
