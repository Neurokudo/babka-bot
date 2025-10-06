#!/usr/bin/env python3
"""
Админ-скрипт для установки баланса пользователя
"""
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import db_subscriptions as db

UID = 5015100177
TARGET = 100

def main():
    print(f"Setting balance for user {UID} to {TARGET} coins...")
    
    # Получаем текущий баланс
    current = db.get_user_balance(UID)
    print(f"Current balance: {current}")
    
    # Вычисляем дельту
    delta = TARGET - current
    print(f"Delta: {delta}")
    
    # Обновляем баланс
    ok = db.update_user_balance(UID, delta, note=f"Admin set balance to {TARGET} (was {current})")
    
    # Проверяем результат
    new_balance = db.get_user_balance(UID)
    
    result = {
        "ok": ok,
        "old": current,
        "delta": delta,
        "new": new_balance
    }
    
    print(f"Result: {result}")
    
    if ok and new_balance == TARGET:
        print("✅ Balance updated successfully!")
    else:
        print("❌ Failed to update balance!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
