#!/usr/bin/env python3
"""
Полное исправление таблицы transactions
Добавляет все недостающие колонки
"""

import os
import psycopg2
from urllib.parse import urlparse

def fix_transactions_table_complete():
    """Полностью исправляет таблицу transactions"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    try:
        # Подключаемся к базе данных
        print("🔗 Подключаемся к базе данных...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Проверяем текущую структуру таблицы
        print("🔍 Проверяем структуру таблицы transactions...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'transactions' 
            ORDER BY ordinal_position
        """)
        
        existing_columns = {row[0] for row in cur.fetchall()}
        print(f"📋 Существующие колонки: {existing_columns}")
        
        # Список всех необходимых колонок
        required_columns = {
            'id': 'SERIAL PRIMARY KEY',
            'user_id': 'BIGINT NOT NULL',
            'type': 'VARCHAR(50) NOT NULL',
            'amount': 'INTEGER NOT NULL',
            'feature': 'VARCHAR(100)',
            'description': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT NOW()'
        }
        
        # Добавляем недостающие колонки
        for column_name, column_def in required_columns.items():
            if column_name not in existing_columns:
                print(f"➕ Добавляем колонку '{column_name}'...")
                
                if column_name == 'id':
                    # Для id используем специальную логику
                    cur.execute("""
                        ALTER TABLE transactions 
                        ADD COLUMN id SERIAL PRIMARY KEY
                    """)
                elif column_name == 'created_at':
                    cur.execute(f"""
                        ALTER TABLE transactions 
                        ADD COLUMN {column_name} TIMESTAMP DEFAULT NOW()
                    """)
                else:
                    cur.execute(f"""
                        ALTER TABLE transactions 
                        ADD COLUMN {column_name} {column_def.split()[0]} NOT NULL DEFAULT 0
                    """)
        
        # Обновляем значения по умолчанию
        print("🔄 Обновляем значения по умолчанию...")
        cur.execute("""
            UPDATE transactions 
            SET type = 'spend' 
            WHERE type IS NULL OR type = ''
        """)
        
        cur.execute("""
            UPDATE transactions 
            SET amount = 0 
            WHERE amount IS NULL
        """)
        
        # Применяем изменения
        conn.commit()
        print("✅ Таблица transactions успешно исправлена")
        
        # Проверяем результат
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'transactions' 
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("\n📋 Финальная структура таблицы transactions:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении таблицы transactions: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Полное исправление таблицы transactions...")
    success = fix_transactions_table_complete()
    if success:
        print("✅ Исправление завершено успешно!")
    else:
        print("❌ Исправление не удалось!")
