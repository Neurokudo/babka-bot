#!/usr/bin/env python3
"""
АУДИТ: Тестирование списания монет
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import charge_feature, get_user_plan
from app.services.billing import can_use_feature

def audit_coin_deduction():
    """Тестировать списание монет"""
    print("🔍 АУДИТ: Тестирование списания монет")
    print("="*60)
    
    # Тест 1: Списание монет за функцию
    print("\n🧪 ТЕСТ 1: Списание монет за функцию")
    user_id = 5015100178  # У нас есть подписка с 120 монетами
    
    try:
        # Проверяем баланс до списания
        plan_data = get_user_plan(user_id)
        print(f"📊 Баланс до списания: {plan_data.get('coins', 0)} монет")
        
        # Списываем монеты за tryon
        success = charge_feature(user_id, "tryon", 3, "Тест списания")
        print(f"✅ Списание tryon (3 монеты): {success}")
        
        # Проверяем баланс после списания
        plan_data = get_user_plan(user_id)
        print(f"📊 Баланс после списания: {plan_data.get('coins', 0)} монет")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Списание за video_generation
    print("\n🧪 ТЕСТ 2: Списание за video_generation")
    try:
        # Проверяем баланс до списания
        plan_data = get_user_plan(user_id)
        print(f"📊 Баланс до списания: {plan_data.get('coins', 0)} монет")
        
        # Списываем монеты за video_generation
        success = charge_feature(user_id, "video_generation", 10, "Тест генерации видео")
        print(f"✅ Списание video_generation (10 монет): {success}")
        
        # Проверяем баланс после списания
        plan_data = get_user_plan(user_id)
        print(f"📊 Баланс после списания: {plan_data.get('coins', 0)} монет")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 3: Попытка списать больше, чем есть
    print("\n🧪 ТЕСТ 3: Попытка списать больше, чем есть")
    try:
        # Проверяем баланс
        plan_data = get_user_plan(user_id)
        current_balance = plan_data.get('coins', 0)
        print(f"📊 Текущий баланс: {current_balance} монет")
        
        # Пытаемся списать больше, чем есть
        success = charge_feature(user_id, "expensive_feature", current_balance + 1000, "Попытка списать слишком много")
        print(f"❌ Списание больше баланса: {success}")
        
        # Проверяем, что баланс не изменился
        plan_data = get_user_plan(user_id)
        print(f"📊 Баланс после неудачного списания: {plan_data.get('coins', 0)} монет")
        
    except Exception as e:
        print(f"✅ Ошибка правильно обработана: {e}")
    
    # Тест 4: Валидация входных данных
    print("\n🧪 ТЕСТ 4: Валидация входных данных")
    invalid_cases = [
        (0, "tryon", 3, "test"),
        (-1, "tryon", 3, "test"),
        (None, "tryon", 3, "test"),
        (user_id, "", 3, "test"),
        (user_id, None, 3, "test"),
        (user_id, "tryon", -1, "test"),
        (user_id, "tryon", None, "test"),
    ]
    
    for user_id_test, feature, cost, note in invalid_cases:
        try:
            success = charge_feature(user_id_test, feature, cost, note)
            print(f"🔐 Неверные данные ({user_id_test}, {feature}, {cost}): {success}")
        except Exception as e:
            print(f"✅ Неверные данные правильно отклонены: {e}")
    
    # Тест 5: Проверка транзакций в БД
    print("\n🧪 ТЕСТ 5: Проверка транзакций в БД")
    try:
        import sqlite3
        conn = sqlite3.connect('babka_bot.db')
        cur = conn.cursor()
        
        # Проверяем таблицу transactions
        cur.execute("SELECT user_id, feature, coins_spent, note FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
        transactions = cur.fetchall()
        
        print("📋 Последние транзакции:")
        for trans in transactions:
            print(f"  - Пользователь {trans[0]}: {trans[1]} - {trans[2]} монет ({trans[3]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка проверки транзакций: {e}")

if __name__ == "__main__":
    audit_coin_deduction()
    print("\n✅ АУДИТ СПИСАНИЯ МОНЕТ ЗАВЕРШЕН")
