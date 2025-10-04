#!/usr/bin/env python3
"""
Скрипт для создания подписки вручную для существующего платежа
"""

import os
import sys
sys.path.append('.')

# Устанавливаем переменные окружения
os.environ['YOOKASSA_SHOP_ID'] = '1176639'
os.environ['YOOKASSA_SECRET_KEY'] = 'live_PDdv14wxc9W36rSeeE8j7c4tsnHw-N-Exnra0lMk2HU'

from app.db.db_subscriptions import create_subscription
from app.services.pricing import get_available_tariffs

def create_manual_subscription():
    """Создать подписку вручную"""
    print("🔧 Создаем подписку вручную...")
    
    user_id = 5015100177
    payment_id = "30737b86-000f-5001-9000-1cc214d9af86"
    plan = "lite"
    coins = 120
    price_rub = 1990
    
    print(f"👤 Пользователь: {user_id}")
    print(f"🆔 ID платежа: {payment_id}")
    print(f"📋 Тариф: {plan}")
    print(f"🎟️ Монет: {coins}")
    print(f"💰 Цена: {price_rub} ₽")
    
    try:
        # Создаем подписку
        success = create_subscription(
            user_id=user_id,
            plan=plan,
            coins=coins,
            price_rub=price_rub,
            duration_days=30,
            payment_id=payment_id
        )
        
        if success:
            print("✅ ПОДПИСКА СОЗДАНА УСПЕШНО!")
            print("🎉 Теперь вы можете пользоваться функциями бота!")
            
            # Проверяем подписку
            from app.db.db_subscriptions import get_user_plan
            plan_data = get_user_plan(user_id)
            print(f"📊 Статус подписки: {plan_data}")
            
        else:
            print("❌ Ошибка при создании подписки")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_manual_subscription()
