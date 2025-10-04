#!/usr/bin/env python3
"""
Тест подключения к базе данных Railway
"""

import os
import sys

def test_connection():
    print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    print("=" * 40)
    
    # Проверяем переменные окружения
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден")
        print("💡 Убедитесь, что вы запускаете скрипт в Railway")
        return False
    
    print(f"✅ DATABASE_URL найден: {database_url[:30]}...")
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Парсим URL
        parsed_url = urlparse(database_url)
        print(f"📊 Host: {parsed_url.hostname}")
        print(f"📊 Port: {parsed_url.port}")
        print(f"📊 Database: {parsed_url.path[1:]}")
        print(f"📊 User: {parsed_url.username}")
        
        # Подключаемся
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password
        )
        
        cur = conn.cursor()
        print("✅ Подключение успешно!")
        
        # Проверяем таблицы
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print(f"📋 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Проверяем колонку is_active
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_active'
        """)
        
        is_active_exists = cur.fetchone()
        if is_active_exists:
            print("✅ Колонка is_active существует")
        else:
            print("❌ Колонка is_active НЕ существует")
            print("💡 Нужно выполнить: ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
        
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 не установлен")
        print("💡 Установите: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n✅ Тест подключения прошел успешно!")
    else:
        print("\n❌ Тест подключения не прошел")
        sys.exit(1)
