#!/usr/bin/env python3
"""
Создание пользователя в базе данных
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import db_conn

def create_user():
    """Создать пользователя"""
    print("🔧 Создаем пользователя...")
    
    user_id = 5015100177
    plan = "lite"
    coins = 120
    
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                print("🗄️ Используем PostgreSQL")
                
                # Создаем пользователя
                cur.execute("""
                    INSERT INTO users (user_id, plan, coins, plan_expiry, auto_renew)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '30 days', TRUE)
                    ON CONFLICT (user_id) DO UPDATE SET
                    plan = EXCLUDED.plan,
                    coins = EXCLUDED.coins,
                    plan_expiry = EXCLUDED.plan_expiry,
                    auto_renew = EXCLUDED.auto_renew
                """, (user_id, plan, coins))
                
            else:
                print("🗄️ Используем SQLite")
                
                # Создаем пользователя
                cur.execute("""
                    INSERT OR REPLACE INTO users (user_id, plan, coins, plan_expiry, auto_renew)
                    VALUES (?, ?, ?, datetime('now', '+30 days'), 1)
                """, (user_id, plan, coins))
            
            conn.commit()
            print("✅ ПОЛЬЗОВАТЕЛЬ СОЗДАН!")
            
            # Проверяем результат
            if is_postgres:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = %s", (user_id,))
            else:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = ?", (user_id,))
            
            result = cur.fetchone()
            if result:
                print(f"📊 Результат: {result}")
                print("🎉 Теперь подписка активна!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_user()
