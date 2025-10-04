#!/usr/bin/env python3
"""
АУДИТ: Проверка схемы базы данных
"""

import os
import sys
sys.path.append('.')

from app.db.db_subscriptions import db_conn

def audit_database_schema():
    """Проверить схему базы данных"""
    print("🔍 АУДИТ: Проверка схемы базы данных")
    print("="*60)
    
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            print(f"🗄️ Тип БД: {'PostgreSQL' if is_postgres else 'SQLite'}")
            
            # Проверяем таблицу users
            print("\n📊 ТАБЛИЦА USERS:")
            if is_postgres:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    ORDER BY ordinal_position
                """)
            else:
                cur.execute("PRAGMA table_info(users)")
            
            users_columns = cur.fetchall()
            print("Колонки:")
            for col in users_columns:
                print(f"  - {col}")
            
            # Проверяем таблицу subscriptions
            print("\n📊 ТАБЛИЦА SUBSCRIPTIONS:")
            if is_postgres:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'subscriptions' 
                    ORDER BY ordinal_position
                """)
            else:
                cur.execute("PRAGMA table_info(subscriptions)")
            
            subs_columns = cur.fetchall()
            print("Колонки:")
            for col in subs_columns:
                print(f"  - {col}")
            
            # Проверяем таблицу transactions
            print("\n📊 ТАБЛИЦА TRANSACTIONS:")
            if is_postgres:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'transactions' 
                    ORDER BY ordinal_position
                """)
            else:
                cur.execute("PRAGMA table_info(transactions)")
            
            trans_columns = cur.fetchall()
            print("Колонки:")
            for col in trans_columns:
                print(f"  - {col}")
            
            # Проверяем индексы
            print("\n🔍 ИНДЕКСЫ:")
            if is_postgres:
                cur.execute("""
                    SELECT indexname, tablename, indexdef
                    FROM pg_indexes 
                    WHERE tablename IN ('users', 'subscriptions', 'transactions')
                """)
            else:
                cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
            
            indexes = cur.fetchall()
            for idx in indexes:
                print(f"  - {idx}")
            
            print("\n✅ АУДИТ СХЕМЫ ЗАВЕРШЕН")
            
    except Exception as e:
        print(f"❌ ОШИБКА АУДИТА СХЕМЫ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    audit_database_schema()
