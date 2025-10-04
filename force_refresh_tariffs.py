#!/usr/bin/env python3
"""
Скрипт для принудительного обновления тарифов и очистки кэша
Используйте если старые тарифы вернулись
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def force_refresh():
    print("🔄 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ТАРИФОВ")
    print("=" * 50)
    
    # 1. Очищаем кэш пользователей
    try:
        from app.services.billing import user_states
        old_count = len(user_states)
        user_states.clear()
        print(f"✅ Очищен кэш пользователей: {old_count} → 0")
    except Exception as e:
        print(f"❌ Ошибка очистки кэша: {e}")
    
    # 2. Перезагружаем модули
    try:
        import importlib
        import app.config.pricing
        import app.services.pricing
        
        importlib.reload(app.config.pricing)
        importlib.reload(app.services.pricing)
        print("✅ Модули тарифов перезагружены")
    except Exception as e:
        print(f"❌ Ошибка перезагрузки модулей: {e}")
    
    # 3. Проверяем актуальные тарифы
    try:
        from app.services.pricing import get_available_tariffs, format_plans_list
        
        tariffs = get_available_tariffs()
        print(f"\n📋 Актуальные тарифы ({len(tariffs)}):")
        for tariff in tariffs:
            print(f"  - {tariff['name']}: {tariff['title']} — {tariff['price_rub']} ₽ → {tariff['coins']} монет")
            
        print(f"\n📝 Форматированный список:")
        print(format_plans_list())
        
    except Exception as e:
        print(f"❌ Ошибка проверки тарифов: {e}")
        return False
    
    # 4. Очищаем глобальный кэш main.py (если доступен)
    try:
        # Это нужно делать только если main.py запущен
        print("\n⚠️  Для полной очистки кэша main.py перезапустите бота")
        print("   или используйте команду /reload_profile в боте")
        
    except Exception as e:
        print(f"❌ Ошибка очистки main.py кэша: {e}")
    
    print("\n🎉 Обновление завершено!")
    print("\n📋 Что делать дальше:")
    print("1. Перезапустите бота (если он запущен)")
    print("2. Или используйте команду /reload_profile в боте")
    print("3. Проверьте тарифы через /plans")
    
    return True

if __name__ == "__main__":
    force_refresh()
