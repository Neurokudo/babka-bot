#!/usr/bin/env python3
"""
Скрипт для проверки подписки пользователя
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import get_user_plan, db_conn

def check_user_subscription(user_id: int):
    """Проверить подписку пользователя"""
    print(f"🔍 Проверяем подписку пользователя {user_id}...")
    
    # Проверяем через get_user_plan
    plan_data = get_user_plan(user_id)
    print(f"📊 Данные из get_user_plan: {plan_data}")
    
    # Проверяем напрямую в базе данных
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("""
                    SELECT user_id, plan, plan_expiry, coins, auto_renew, created_at 
                    FROM users WHERE user_id = %s
                """, (user_id,))
            else:
                cur.execute("""
                    SELECT user_id, plan, plan_expiry, coins, auto_renew, created_at 
                    FROM users WHERE user_id = ?
                """, (user_id,))
            
            result = cur.fetchone()
            if result:
                print(f"🗄️ Данные из БД: {result}")
            else:
                print("❌ Пользователь не найден в БД")
                
            # Проверяем таблицу subscriptions
            if is_postgres:
                cur.execute("""
                    SELECT user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id
                    FROM subscriptions WHERE user_id = %s ORDER BY start_date DESC
                """, (user_id,))
            else:
                cur.execute("""
                    SELECT user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id
                    FROM subscriptions WHERE user_id = ? ORDER BY start_date DESC
                """, (user_id,))
            
            subscriptions = cur.fetchall()
            if subscriptions:
                print(f"💳 Подписки в БД: {subscriptions}")
            else:
                print("❌ Подписок не найдено в БД")
                
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")

if __name__ == "__main__":
    user_id = 5015100177  # Ваш ID
    check_user_subscription(user_id)
