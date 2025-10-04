#!/usr/bin/env python3
"""
Простое создание подписки
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import db_conn

def create_subscription_simple():
    """Создать подписку простым способом"""
    print("🔧 Создаем подписку простым способом...")
    
    user_id = 5015100177
    payment_id = "30737b86-000f-5001-9000-1cc214d9af86"
    plan = "lite"
    coins = 120
    price_rub = 1990
    
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                print("🗄️ Используем PostgreSQL")
                
                # Создаем подписку
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days', TRUE, %s)
                """, (user_id, plan, coins, price_rub, payment_id))
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = %s, plan_expiry = CURRENT_TIMESTAMP + INTERVAL '30 days', coins = coins + %s
                    WHERE user_id = %s
                """, (plan, coins, user_id))
                
            else:
                print("🗄️ Используем SQLite")
                
                # Создаем подписку
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now', '+30 days'), 1, ?)
                """, (user_id, plan, coins, price_rub, payment_id))
                
                # Обновляем пользователя
                cur.execute("""
                    UPDATE users
                    SET plan = ?, plan_expiry = datetime('now', '+30 days'), coins = coins + ?
                    WHERE user_id = ?
                """, (plan, coins, user_id))
            
            conn.commit()
            print("✅ ПОДПИСКА СОЗДАНА УСПЕШНО!")
            print(f"👤 Пользователь: {user_id}")
            print(f"📋 Тариф: {plan}")
            print(f"🎟️ Монет: {coins}")
            print(f"💰 Цена: {price_rub} ₽")
            print(f"⏰ Длительность: 30 дней")
            
            # Проверяем результат
            if is_postgres:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = %s", (user_id,))
            else:
                cur.execute("SELECT plan, coins, plan_expiry FROM users WHERE user_id = ?", (user_id,))
            
            result = cur.fetchone()
            if result:
                print(f"📊 Результат: {result}")
                print("🎉 Теперь вы можете пользоваться функциями бота!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_subscription_simple()
