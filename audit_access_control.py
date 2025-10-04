#!/usr/bin/env python3
"""
АУДИТ: Тестирование проверки доступа к функциям
"""

import os
import sys
sys.path.append('.')

from app.services.billing import can_use_feature, has_active_subscription
from app.db.db_subscriptions import get_user_plan

def audit_access_control():
    """Тестировать проверку доступа к функциям"""
    print("🔍 АУДИТ: Тестирование проверки доступа к функциям")
    print("="*60)
    
    # Тест 1: Пользователь с активной подпиской
    print("\n🧪 ТЕСТ 1: Пользователь с активной подпиской")
    user_id = 5015100178  # У нас есть подписка lite
    
    try:
        # Проверяем подписку
        plan_data = get_user_plan(user_id)
        print(f"📊 Данные подписки: {plan_data}")
        
        # Проверяем доступ к функциям
        access_check = can_use_feature(user_id, "tryon")
        print(f"🔐 Доступ к tryon: {access_check}")
        
        access_check = can_use_feature(user_id, "video_generation")
        print(f"🔐 Доступ к video_generation: {access_check}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Пользователь без подписки
    print("\n🧪 ТЕСТ 2: Пользователь без подписки")
    user_id = 9999999999  # Несуществующий пользователь
    
    try:
        plan_data = get_user_plan(user_id)
        print(f"📊 Данные подписки: {plan_data}")
        
        access_check = can_use_feature(user_id, "tryon")
        print(f"🔐 Доступ к tryon: {access_check}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 3: Пользователь с недостаточным балансом
    print("\n🧪 ТЕСТ 3: Пользователь с недостаточным балансом")
    user_id = 5015100178  # У нас есть подписка, но проверим недостаток монет
    
    try:
        # Проверяем доступ к дорогой функции
        access_check = can_use_feature(user_id, "video_generation")  # Очень дорого
        print(f"🔐 Доступ к дорогой функции: {access_check}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 4: Разные типы функций
    print("\n🧪 ТЕСТ 4: Разные типы функций")
    user_id = 5015100178
    
    functions = [
        "tryon",
        "video_generation", 
        "bg_removal",
        "photo_enhancement",
    ]
    
    for func_name in functions:
        try:
            access_check = can_use_feature(user_id, func_name)
            print(f"🔐 {func_name}: {access_check}")
        except Exception as e:
            print(f"❌ Ошибка для {func_name}: {e}")
    
    # Тест 5: Валидация входных данных
    print("\n🧪 ТЕСТ 5: Валидация входных данных")
    
    invalid_cases = [
        (0, "tryon"),
        (-1, "tryon"),
        (None, "tryon"),
        (5015100178, ""),
        (5015100178, None),
    ]
    
    for user_id, func_name in invalid_cases:
        try:
            access_check = can_use_feature(user_id, func_name)
            print(f"🔐 Неверные данные ({user_id}, {func_name}): {access_check}")
        except Exception as e:
            print(f"✅ Неверные данные правильно отклонены: {e}")

if __name__ == "__main__":
    audit_access_control()
    print("\n✅ АУДИТ ПРОВЕРКИ ДОСТУПА ЗАВЕРШЕН")
