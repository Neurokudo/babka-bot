#!/usr/bin/env python3
"""
Скрипт для восстановления баланса пользователя до 100 монет
"""

import os
import sys
sys.path.append('.')

from app.db.queries import db_manager

def restore_balance_to_100(user_id: int):
    """Восстановить баланс пользователя до 100 монет"""
    print(f"🔍 Проверяем текущий баланс пользователя {user_id}...")
    
    # Получаем текущий баланс
    current_balance = db_manager.get_user_balance(user_id)
    print(f"💰 Текущий баланс: {current_balance} монет")
    
    if current_balance == 100:
        print("✅ Баланс уже равен 100 монетам!")
        return True
    
    # Вычисляем разность
    difference = 100 - current_balance
    print(f"📊 Нужно изменить баланс на: {difference} монет")
    
    if difference > 0:
        # Добавляем монеты
        print(f"➕ Добавляем {difference} монет...")
        success = db_manager.add_coins(user_id, difference)
        if success:
            print(f"✅ Успешно добавлено {difference} монет!")
        else:
            print(f"❌ Ошибка при добавлении монет")
            return False
    else:
        # Убираем монеты (списываем)
        print(f"➖ Списываем {abs(difference)} монет...")
        success = db_manager.spend_coins(user_id, abs(difference), "balance_restore")
        if success:
            print(f"✅ Успешно списано {abs(difference)} монет!")
        else:
            print(f"❌ Ошибка при списании монет")
            return False
    
    # Проверяем итоговый баланс
    final_balance = db_manager.get_user_balance(user_id)
    print(f"🎯 Итоговый баланс: {final_balance} монет")
    
    if final_balance == 100:
        print("✅ Баланс успешно восстановлен до 100 монет!")
        return True
    else:
        print(f"❌ Ошибка: ожидалось 100 монет, получено {final_balance}")
        return False

if __name__ == "__main__":
    user_id = 5015100177  # Ваш ID
    print("🚀 Начинаем восстановление баланса...")
    success = restore_balance_to_100(user_id)
    
    if success:
        print("🎉 Операция завершена успешно!")
    else:
        print("💥 Операция завершилась с ошибкой!")
        sys.exit(1)
