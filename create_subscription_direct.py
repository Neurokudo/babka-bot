#!/usr/bin/env python3
"""
Прямое создание подписки через SQL
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import db_conn

def create_subscription_direct():
    """Создать подписку напрямую через SQL"""
    print("🔧 Создаем подписку напрямую...")
    
    user_id = 5015100177
    payment_id = "30737b86-000f-5001-9000-1cc214d9af86"
    plan = "lite"
    coins = 120
    price_rub = 1990
    duration_days = 30
    
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                # PostgreSQL
                print("🗄️ Используем PostgreSQL")
                
                # Создаем подписку
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id)
                    VALUES (%s, %s, %s, %s, datetime("now"), datetime("now") + (%s || ' days')::interval, TRUE, %s)
                """, (user_id, plan, coins, price_rub, duration_days, payment_id))
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = %s, plan_expiry = datetime("now") + (%s || ' days')::interval, coins = coins + %s
                    WHERE user_id = %s
                """, (plan, duration_days, coins, user_id))
                
            else:
                # SQLite
                print("🗄️ Используем SQLite")
                
                # Создаем подписку
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id)
                    VALUES (?, ?, ?, ?, datetime("now"), datetime('now', '+? days'), 1, ?)
                """, (user_id, plan, coins, price_rub, duration_days, payment_id))
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = ?, plan_expiry = datetime('now', '+? days'), coins = coins + ?
                    WHERE user_id = ?
                """, (plan, duration_days, coins, user_id))
            
            conn.commit()
            print("✅ ПОДПИСКА СОЗДАНА УСПЕШНО!")
            print(f"👤 Пользователь: {user_id}")
            print(f"📋 Тариф: {plan}")
            print(f"🎟️ Монет: {coins}")
            print(f"💰 Цена: {price_rub} ₽")
            print(f"⏰ Длительность: {duration_days} дней")
            
            # Проверяем результат
            if is_postgres:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = %s", (user_id,))
            else:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = ?", (user_id,))
            
            result = cur.fetchone()
            if result:
                print(f"📊 Результат: {result}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_subscription_direct()
