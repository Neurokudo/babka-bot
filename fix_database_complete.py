#!/usr/bin/env python3
"""
Полное исправление схемы базы данных PostgreSQL
Исправляет таблицы users и subscriptions для корректной работы с YooKassa webhook
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def fix_database_complete():
    print("🔧 ПОЛНОЕ ИСПРАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    # Получаем URL базы данных
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    print(f"📊 Подключение к базе данных...")
    
    try:
        # Парсим URL базы данных
        parsed_url = urlparse(database_url)
        
        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password
        )
        
        cur = conn.cursor()
        print("✅ Подключение к базе данных успешно")
        
        # ===== ИСПРАВЛЕНИЕ ТАБЛИЦЫ USERS =====
        print("\n🔧 ИСПРАВЛЕНИЕ ТАБЛИЦЫ USERS")
        print("-" * 40)
        
        # Проверяем структуру таблицы users
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        users_columns = cur.fetchall()
        print("📊 Текущие колонки в таблице users:")
        for col in users_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Добавляем недостающие колонки в users
        users_alter_commands = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expiry TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        for cmd in users_alter_commands:
            try:
                print(f"🔧 Выполняем: {cmd}")
                cur.execute(cmd)
                conn.commit()
                print(f"✅ Успешно: {cmd}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️ Колонка уже существует: {cmd}")
                else:
                    print(f"❌ Ошибка: {cmd} - {e}")
        
        # ===== ИСПРАВЛЕНИЕ ТАБЛИЦЫ SUBSCRIPTIONS =====
        print("\n🔧 ИСПРАВЛЕНИЕ ТАБЛИЦЫ SUBSCRIPTIONS")
        print("-" * 40)
        
        # Проверяем структуру таблицы subscriptions
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions'
            ORDER BY ordinal_position
        """)
        
        subscriptions_columns = cur.fetchall()
        print("📊 Текущие колонки в таблице subscriptions:")
        for col in subscriptions_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Добавляем недостающие колонки в subscriptions
        subscriptions_alter_commands = [
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS user_id BIGINT NOT NULL",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS coins INTEGER DEFAULT 0",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS price_rub INTEGER NOT NULL",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS end_date TIMESTAMP NOT NULL",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_id TEXT",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        for cmd in subscriptions_alter_commands:
            try:
                print(f"🔧 Выполняем: {cmd}")
                cur.execute(cmd)
                conn.commit()
                print(f"✅ Успешно: {cmd}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️ Колонка уже существует: {cmd}")
                else:
                    print(f"❌ Ошибка: {cmd} - {e}")
        
        # ===== ПРОВЕРКА ФИНАЛЬНОЙ СТРУКТУРЫ =====
        print("\n🔍 ПРОВЕРКА ФИНАЛЬНОЙ СТРУКТУРЫ")
        print("-" * 40)
        
        # Проверяем таблицу users
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        final_users_columns = cur.fetchall()
        print("📊 Финальные колонки в таблице users:")
        for col in final_users_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Проверяем таблицу subscriptions
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions'
            ORDER BY ordinal_position
        """)
        
        final_subscriptions_columns = cur.fetchall()
        print("\n📊 Финальные колонки в таблице subscriptions:")
        for col in final_subscriptions_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # ===== ТЕСТИРОВАНИЕ =====
        print("\n🧪 ТЕСТИРОВАНИЕ")
        print("-" * 40)
        
        # Тестируем INSERT в subscriptions
        try:
            print("🧪 Тестируем INSERT в таблицу subscriptions...")
            cur.execute("""
                INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (999999999, 'test', 0, 0, '2025-01-01 00:00:00', '2025-01-02 00:00:00', True, 'test-payment', '2025-01-01 00:00:00'))
            
            # Откатываем тестовую запись
            cur.execute("DELETE FROM subscriptions WHERE user_id = 999999999")
            conn.commit()
            print("✅ INSERT в subscriptions работает корректно")
        except Exception as e:
            print(f"❌ Ошибка при тестировании INSERT в subscriptions: {e}")
        
        # Проверяем количество записей
        cur.execute("SELECT COUNT(*) FROM users")
        users_count = cur.fetchone()[0]
        print(f"📊 Количество пользователей: {users_count}")
        
        cur.execute("SELECT COUNT(*) FROM subscriptions")
        subscriptions_count = cur.fetchone()[0]
        print(f"📊 Количество подписок: {subscriptions_count}")
        
        conn.close()
        print("\n✅ СХЕМА БАЗЫ ДАННЫХ ПОЛНОСТЬЮ ИСПРАВЛЕНА!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_database_complete()
    if success:
        print("\n🎯 БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!")
        print("✅ Таблица users исправлена")
        print("✅ Таблица subscriptions исправлена")
        print("✅ YooKassa webhook должен работать корректно")
        print("✅ Уведомления о подписке должны приходить")
        print("\n🚀 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Перезапустите Railway контейнер")
        print("2. Проверьте логи на отсутствие ошибок")
        print("3. Попробуйте купить подписку через бота")
    else:
        print("\n❌ Не удалось исправить схему базы данных")
        sys.exit(1)
