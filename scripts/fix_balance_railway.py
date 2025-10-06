#!/usr/bin/env python3
"""
Скрипт для исправления баланса пользователя в Railway PostgreSQL
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_balance_railway():
    """Исправить баланс в Railway PostgreSQL"""
    print("🔧 Исправление баланса в Railway PostgreSQL...")
    
    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    print(f"📊 DATABASE_URL: {database_url[:20]}...")
    
    try:
        from app.db import db_subscriptions as db
        
        UID = 5015100177
        TARGET = 100
        
        # Получаем текущий баланс
        current = db.get_user_balance(UID)
        print(f"💰 Текущий баланс: {current}")
        
        # Вычисляем дельту
        delta = TARGET - current
        print(f"📈 Дельта: {delta}")
        
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
        
        print(f"✅ Результат: {result}")
        
        if ok and new_balance == TARGET:
            print("🎉 Баланс успешно обновлен в Railway!")
            return True
        else:
            print("❌ Не удалось обновить баланс!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_balance_direct_sql():
    """Прямое исправление через SQL (fallback)"""
    print("🔧 Прямое исправление через SQL...")
    
    try:
        import psycopg2
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL не найден")
            return False
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        UID = 5015100177
        TARGET = 100
        
        # Получаем текущий баланс
        cur.execute("SELECT coins FROM users WHERE user_id = %s", (UID,))
        result = cur.fetchone()
        
        if not result:
            print(f"❌ Пользователь {UID} не найден")
            return False
        
        current = result[0]
        print(f"💰 Текущий баланс: {current}")
        
        # Обновляем баланс
        cur.execute("UPDATE users SET coins = %s WHERE user_id = %s", (TARGET, UID))
        
        # Добавляем запись в транзакции
        cur.execute("""
            INSERT INTO transactions(user_id, feature, coins_spent, note)
            VALUES (%s, 'balance_update', 0, %s)
        """, (UID, f"Admin set balance to {TARGET} (was {current})"))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Баланс установлен в {TARGET} монет")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка SQL: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Исправление баланса пользователя 5015100177 = 100 монет\n")
    
    # Пробуем через db_subscriptions
    if fix_balance_railway():
        return 0
    
    print("\n🔄 Fallback: прямое исправление через SQL...")
    if fix_balance_direct_sql():
        return 0
    
    print("\n❌ Не удалось исправить баланс")
    return 1

if __name__ == "__main__":
    exit(main())
