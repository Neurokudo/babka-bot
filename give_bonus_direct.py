#!/usr/bin/env python3
"""
Скрипт для прямого начисления бонусов администратору
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def give_bonuses():
    """Начислить бонусы пользователю"""
    ADMIN_ID = 5015100177
    
    print("🎁 НАЧИСЛЕНИЕ ТЕСТОВЫХ БОНУСОВ")
    print("=" * 40)
    
    # Получаем данные пользователя
    user_data = db.get_user(ADMIN_ID)
    
    if not user_data:
        print(f"❌ Пользователь {ADMIN_ID} не найден в базе данных")
        print("   Возможно, вы еще не запускали бота")
        print("   Запустите бота и напишите /start")
        return False
    
    print(f"✅ Пользователь найден: {ADMIN_ID}")
    print(f"\n📊 Текущие бонусы:")
    print(f"   Видео: {user_data.get('video_bonus', 0)}")
    print(f"   Фото: {user_data.get('photo_bonus', 0)}")
    print(f"   Примерки: {user_data.get('tryon_bonus', 0)}")
    print(f"   Монетки: {user_data.get('coins', 0)}")
    
    # Начисляем бонусы
    user_data["video_bonus"] = user_data.get("video_bonus", 0) + 30
    user_data["photo_bonus"] = user_data.get("photo_bonus", 0) + 50
    user_data["tryon_bonus"] = user_data.get("tryon_bonus", 0) + 10
    user_data["coins"] = user_data.get("coins", 0) + 500
    
    # Сохраняем в базу
    db.save_user(ADMIN_ID, user_data)
    
    print(f"\n✨ БОНУСЫ НАЧИСЛЕНЫ:")
    print(f"   Видео: {user_data['video_bonus']} (+30)")
    print(f"   Фото: {user_data['photo_bonus']} (+50)")
    print(f"   Примерки: {user_data['tryon_bonus']} (+10)")
    print(f"   Монетки: {user_data['coins']} (+500)")
    
    print(f"\n🎉 Готово! Проверьте баланс в боте командой /start")
    return True

if __name__ == "__main__":
    try:
        success = give_bonuses()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

