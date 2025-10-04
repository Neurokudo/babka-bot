#!/usr/bin/env python3
"""
Простая проверка платежа без интерактивного ввода
"""

import os
import sys
sys.path.append('.')

# Устанавливаем переменные окружения для тестирования
os.environ['YOOKASSA_SHOP_ID'] = '1176639'
os.environ['YOOKASSA_SECRET_KEY'] = 'live_PDdv14wxc9W36rSeeE8j7c4tsnHw-N-Exnra0lMk2HU'

from app.services.yookassa_service import check_payment_status

def check_payment_by_id(payment_id: str):
    """Проверить платеж по ID"""
    print(f"🔍 Проверяем платеж {payment_id}...")
    
    try:
        status = check_payment_status(payment_id)
        
        print("="*60)
        print("📊 РЕЗУЛЬТАТ ПРОВЕРКИ ПЛАТЕЖА:")
        print("="*60)
        print(f"🆔 ID платежа: {status.get('payment_id', 'N/A')}")
        print(f"📊 Статус: {status.get('status', 'unknown')}")
        print(f"💰 Сумма: {status.get('amount', 0)} {status.get('currency', 'RUB')}")
        print(f"📝 Описание: {status.get('description', 'N/A')}")
        print(f"🏷️ Метаданные: {status.get('metadata', {})}")
        print(f"📅 Создан: {status.get('created_at', 'N/A')}")
        print(f"✅ Оплачен: {status.get('paid', False)}")
        print("="*60)
        
        if status.get('status') == 'succeeded':
            print("✅ ПЛАТЕЖ УСПЕШЕН!")
            print("🔍 Проверяем метаданные...")
            
            metadata = status.get('metadata', {})
            user_id = metadata.get('user_id')
            plan = metadata.get('plan')
            coins = metadata.get('coins')
            
            if user_id:
                print(f"👤 Пользователь: {user_id}")
                print(f"📋 Тариф: {plan}")
                print(f"🎟️ Монет: {coins}")
                
                if user_id == '5015100177':
                    print("✅ Это ваш платеж!")
                    print("❌ Но webhook не сработал - подписка не создалась")
                    print("🔧 НУЖНО НАСТРОИТЬ WEBHOOK В YOOKASSA!")
                    print("🌐 URL webhook: https://ваш-домен.railway.app/webhook/yookassa")
                else:
                    print("❌ Это не ваш платеж")
            else:
                print("❌ Нет метаданных пользователя")
                
        elif status.get('status') == 'pending':
            print("⏳ ПЛАТЕЖ ОЖИДАЕТ ОПЛАТЫ")
            print("💳 Перейдите по ссылке и оплатите")
            
        else:
            print(f"❌ ПЛАТЕЖ НЕ УСПЕШЕН: {status.get('status')}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке платежа: {e}")
        print("💡 Возможные причины:")
        print("   - Неправильный ID платежа")
        print("   - Платеж не существует")
        print("   - Проблемы с API YooKassa")

if __name__ == "__main__":
    print("🔍 ПРОВЕРКА ПЛАТЕЖА ПО ID")
    print("="*40)
    
    # ID вашего платежа
    payment_id = "30737b86-000f-5001-9000-1cc214d9af86"
    
    if payment_id == "ЗАМЕНИТЕ_НА_РЕАЛЬНЫЙ_ID_ПЛАТЕЖА":
        print("❌ Сначала замените payment_id в коде на реальный ID платежа")
        print("💡 ID платежа можно найти в личном кабинете YooKassa:")
        print("   https://yookassa.ru/my")
        print("   Перейдите в 'Платежи' и найдите ваш платеж")
        sys.exit(1)
    
    check_payment_by_id(payment_id)
