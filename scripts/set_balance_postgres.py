#!/usr/bin/env python3
"""
Скрипт для установки баланса пользователя в PostgreSQL Railway
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set in this shell")
        return

    print(f"🔧 Connecting to PostgreSQL: {DATABASE_URL[:20]}...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        uid = 5015100177

        # Получаем текущий баланс
        cur.execute("SELECT coins FROM users WHERE user_id = %s", (uid,))
        result = cur.fetchone()
        
        if not result:
            print(f"❌ User {uid} not found in database")
            return
        
        old = result[0]
        print(f"💰 Current balance: {old}")

        # Обновляем баланс
        cur.execute("UPDATE users SET coins = 100 WHERE user_id = %s", (uid,))
        
        # Добавляем запись в транзакции
        cur.execute("""
            INSERT INTO transactions(user_id, feature, coins_spent, note)
            VALUES (%s, 'balance_update', 0, %s)
        """, (uid, f'Admin set balance to 100 (was {old})'))

        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Balance updated: old={old}, new=100")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
