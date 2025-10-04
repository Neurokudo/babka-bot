#!/usr/bin/env python3
"""
Скрипт для исправления схемы базы данных
Добавляет отсутствующую колонку is_active в таблицу users
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def fix_database_schema():
    print("🔧 ИСПРАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Получаем URL базы данных
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    print(f"📊 Подключение к базе данных: {database_url[:20]}...")
    
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
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE
            """)
            conn.commit()
            print("✅ Колонка is_active добавлена успешно")
        
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
        cur.execute("SELECT * FROM users LIMIT 1")
        sample_data = cur.fetchone()
        
        if sample_data:
            print("✅ Данные в таблице users найдены")
            print(f"📊 Пример записи: {sample_data}")
        else:
            print("ℹ️ Таблица users пуста")
        
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
            cur.execute("SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 1")
            latest_sub = cur.fetchone()
            print(f"📊 Последняя подписка: {latest_sub}")
        
        conn.close()
        print("\n✅ СХЕМА БАЗЫ ДАННЫХ ИСПРАВЛЕНА УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Перезапустите Railway контейнер")
        print("2. Проверьте логи на отсутствие ошибок")
        print("3. Попробуйте купить подписку")
        print("4. Убедитесь, что приходит уведомление")
    else:
        print("\n❌ Не удалось исправить схему базы данных")
        sys.exit(1)
