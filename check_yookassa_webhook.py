#!/usr/bin/env python3
"""
Скрипт для проверки webhook YooKassa
"""

import os
import sys
sys.path.append('.')

from app.services.yookassa_service import check_payment_status

def check_payment(payment_id: str):
    """Проверить статус платежа в YooKassa"""
    print(f"🔍 Проверяем платеж {payment_id} в YooKassa...")
    
    try:
        status = check_payment_status(payment_id)
        print(f"📊 Статус платежа: {status}")
        
        if status.get('status') == 'succeeded':
            print("✅ Платеж успешен!")
            print(f"💰 Сумма: {status.get('amount')} {status.get('currency')}")
            print(f"📝 Описание: {status.get('description')}")
            print(f"🏷️ Метаданные: {status.get('metadata')}")
        else:
            print(f"❌ Платеж не успешен: {status.get('status')}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке платежа: {e}")

if __name__ == "__main__":
    # Вставьте сюда ID вашего платежа из YooKassa
    # Обычно он выглядит как "2c7c4c8a-0000-4000-8000-123456789012"
    payment_id = input("Введите ID платежа из YooKassa: ").strip()
    
    if payment_id:
        check_payment(payment_id)
    else:
        print("❌ ID платежа не введен")
