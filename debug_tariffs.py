#!/usr/bin/env python3
"""
Скрипт для диагностики проблем с тарифами
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_tariffs():
    print("🔍 ДИАГНОСТИКА ТАРИФОВ")
    print("=" * 50)
    
    # 1. Проверяем импорты
    try:
        from app.config.pricing import TARIFFS, TOPUP_PACKS
        print("✅ app.config.pricing импорт работает")
        
        for name, tariff in TARIFFS.items():
            print(f"  - {name}: {tariff.price_rub} ₽ → {tariff.coins} монет")
            
        print(f"  Пакеты монет: {len(TOPUP_PACKS)} штук")
        for pack in TOPUP_PACKS:
            print(f"    - {pack.coins} монет — {pack.price_rub} ₽")
            
    except Exception as e:
        print(f"❌ Ошибка импорта app.config.pricing: {e}")
        return False
    
    # 2. Проверяем сервис pricing
    try:
        from app.services.pricing import get_available_tariffs, format_plans_list
        print("\n✅ app.services.pricing импорт работает")
        
        tariffs = get_available_tariffs()
        print(f"  Доступно тарифов: {len(tariffs)}")
        for tariff in tariffs:
            print(f"    - {tariff['name']}: {tariff['title']} — {tariff['price_rub']} ₽ → {tariff['coins']} монет")
            
        print("\n📋 Форматированный список:")
        print(format_plans_list())
        
    except Exception as e:
        print(f"❌ Ошибка app.services.pricing: {e}")
        return False
    
    # 3. Проверяем базу данных
    try:
        from app.db import db_subscriptions as db
        print("\n✅ База данных доступна")
        
        # Проверяем структуру таблиц
        with db.db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
            print(f"  Таблицы: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    
    # 4. Проверяем кэш пользователей
    try:
        from app.services.billing import user_states
        print(f"\n✅ Кэш пользователей: {len(user_states)} пользователей")
        
        if user_states:
            print("  Примеры пользователей:")
            for user_id, state in list(user_states.items())[:3]:
                print(f"    - {user_id}: {state.get('coins', 0)} монет, план: {state.get('tariff', 'нет')}")
                
    except Exception as e:
        print(f"❌ Ошибка кэша пользователей: {e}")
        return False
    
    print("\n🎉 Диагностика завершена успешно!")
    return True

if __name__ == "__main__":
    check_tariffs()
