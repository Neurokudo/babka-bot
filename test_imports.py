#!/usr/bin/env python3
"""
Тест импортов для проверки совместимости
"""

def test_imports():
    """Проверка всех основных импортов"""
    try:
        # Основные импорты
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        print("✅ telegram импорт работает")
        
        from app.services.pricing import feature_cost_coins, get_available_tariffs
        print("✅ app.services.pricing импорт работает")
        
        from app.services.wallet import get_balance, charge_feature
        print("✅ app.services.wallet импорт работает")
        
        from app.services.billing import can_spend, hold_and_start
        print("✅ app.services.billing импорт работает")
        
        from app.services.clients.veo_client import generate_video_sync
        print("✅ app.services.clients.veo_client импорт работает")
        
        from app.utils.logging import setup_logging
        print("✅ app.utils.logging импорт работает")
        
        print("\n🎉 Все импорты работают корректно!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    test_imports()
