#!/usr/bin/env python3
"""
Скрипт для тестирования создания платежа и проверки webhook'а
"""

import os
import sys
sys.path.append('.')

from app.services.yookassa_service import create_payment, check_payment_status

def test_payment_creation():
    """Создать тестовый платеж"""
    print("🧪 Создаем тестовый платеж...")
    
    try:
        user_id = 5015100177  # Ваш ID
        plan = "lite"
        price_rub = 1990
        coins = 120
        
        # Создаем платеж
        payment_url, payment_id = create_payment(
            user_id=user_id,
            plan=plan,
            price_rub=price_rub,
            coins=coins,
            username="test_user"
        )
        
        print(f"✅ Платеж создан!")
        print(f"🆔 ID платежа: {payment_id}")
        print(f"🔗 URL для оплаты: {payment_url}")
        print(f"💰 Сумма: {price_rub} ₽")
        print(f"🎟️ Монет: {coins}")
        
        return payment_id
        
    except Exception as e:
        print(f"❌ Ошибка при создании платежа: {e}")
        return None

def check_payment_status_safe(payment_id: str):
    """Безопасно проверить статус платежа"""
    print(f"🔍 Проверяем статус платежа {payment_id}...")
    
    try:
        status = check_payment_status(payment_id)
        print(f"📊 Статус: {status.get('status', 'unknown')}")
        print(f"💰 Сумма: {status.get('amount', 0)} {status.get('currency', 'RUB')}")
        print(f"📝 Описание: {status.get('description', 'N/A')}")
        print(f"🏷️ Метаданные: {status.get('metadata', {})}")
        
        if status.get('status') == 'succeeded':
            print("✅ Платеж успешен!")
            return True
        elif status.get('status') == 'pending':
            print("⏳ Платеж ожидает оплаты")
            return False
        else:
            print(f"❌ Платеж не успешен: {status.get('status')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке статуса: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Тестирование платежной системы...")
    
    # Создаем тестовый платеж
    payment_id = test_payment_creation()
    
    if payment_id:
        print("\n" + "="*50)
        print("📋 ИНСТРУКЦИЯ:")
        print("1. Перейдите по ссылке выше")
        print("2. Оплатите платеж")
        print("3. Вернитесь сюда и нажмите Enter")
        print("="*50)
        
        input("Нажмите Enter после оплаты...")
        
        # Проверяем статус
        check_payment_status_safe(payment_id)
    else:
        print("❌ Не удалось создать платеж")
