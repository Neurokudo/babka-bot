#!/usr/bin/env python3
"""
Исправление подписки пользователя
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import db_conn

def fix_user_subscription():
    """Исправить подписку пользователя"""
    print("🔧 Исправляем подписку пользователя...")
    
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
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = %s, plan_expiry = CURRENT_TIMESTAMP + INTERVAL '30 days', coins = %s
                    WHERE user_id = %s
                """, (plan, coins, user_id))
                
            else:
                print("🗄️ Используем SQLite")
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = ?, plan_expiry = datetime('now', '+30 days'), coins = ?
                    WHERE user_id = ?
                """, (plan, coins, user_id))
            
            conn.commit()
            print("✅ ПОДПИСКА ИСПРАВЛЕНА!")
            
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
    fix_user_subscription()
