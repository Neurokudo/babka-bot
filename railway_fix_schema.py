#!/usr/bin/env python3
"""
Скрипт для исправления схемы базы данных в Railway
Добавляет отсутствующую колонку is_active в таблицу users
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def fix_database_schema():
    print("🔧 ИСПРАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ В RAILWAY")
    print("=" * 60)
    
    # Получаем URL базы данных из переменных окружения Railway
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        print("💡 Убедитесь, что вы запускаете скрипт в Railway")
        return False
    
    print(f"📊 Подключение к базе данных Railway...")
    
    try:
        # Парсим URL базы данных
        parsed_url = urlparse(database_url)
        
        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],  # убираем первый символ '/'
            user=parsed_url.username,
            password=parsed_url.password
        )
        
        cur = conn.cursor()
        print("✅ Подключение к базе данных успешно")
        
        # Шаг 1: Проверяем существование колонки is_active
        print("\n🔍 ШАГ 1: Проверка существования колонки is_active")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_active'
        """)
        
        column_exists = cur.fetchone()
        if column_exists:
            print("✅ Колонка is_active уже существует")
        else:
            print("❌ Колонка is_active не найдена")
            
            # Шаг 2: Добавляем колонку is_active
            print("\n🔧 ШАГ 2: Добавление колонки is_active")
            try:
                cur.execute("""
                    ALTER TABLE users
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """)
                conn.commit()
                print("✅ Колонка is_active добавлена успешно")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("✅ Колонка is_active уже существует (игнорируем ошибку)")
                else:
                    print(f"❌ Ошибка при добавлении колонки: {e}")
                    return False
        
        # Шаг 3: Проверяем структуру таблицы users
        print("\n📋 ШАГ 3: Проверка структуры таблицы users")
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("📊 Колонки в таблице users:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Шаг 4: Проверяем данные в таблице
        print("\n🔍 ШАГ 4: Проверка данных в таблице users")
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        print(f"📊 Количество пользователей: {user_count}")
        
        if user_count > 0:
            cur.execute("SELECT user_id, username, is_active FROM users LIMIT 3")
            sample_data = cur.fetchall()
            print("📊 Примеры записей:")
            for row in sample_data:
                print(f"  - ID: {row[0]}, Username: {row[1]}, is_active: {row[2]}")
        
        # Шаг 5: Проверяем таблицу subscriptions
        print("\n🔍 ШАГ 5: Проверка таблицы subscriptions")
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions'
            ORDER BY ordinal_position
        """)
        
        sub_columns = cur.fetchall()
        print("📊 Колонки в таблице subscriptions:")
        for col in sub_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Шаг 6: Проверяем данные в subscriptions
        cur.execute("SELECT COUNT(*) FROM subscriptions")
        sub_count = cur.fetchone()[0]
        print(f"📊 Количество записей в subscriptions: {sub_count}")
        
        if sub_count > 0:
            cur.execute("SELECT user_id, plan, is_active, created_at FROM subscriptions ORDER BY created_at DESC LIMIT 3")
            latest_subs = cur.fetchall()
            print("📊 Последние подписки:")
            for row in latest_subs:
                print(f"  - User: {row[0]}, Plan: {row[1]}, Active: {row[2]}, Created: {row[3]}")
        
        conn.close()
        print("\n✅ СХЕМА БАЗЫ ДАННЫХ ИСПРАВЛЕНА УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n🎯 СХЕМА БАЗЫ ДАННЫХ ГОТОВА!")
        print("✅ Колонка is_active добавлена в таблицу users")
        print("✅ Теперь webhook от YooKassa должен работать корректно")
        print("✅ Уведомления о подписке должны приходить")
    else:
        print("\n❌ Не удалось исправить схему базы данных")
        sys.exit(1)
