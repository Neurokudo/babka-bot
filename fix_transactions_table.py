#!/usr/bin/env python3
"""
Скрипт для исправления таблицы transactions
Добавляет недостающую колонку 'type'
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def fix_transactions_table():
    """Исправляет таблицу transactions, добавляя колонку type"""
    
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
        
        # Проверяем, существует ли колонка 'type'
        print("🔍 Проверяем структуру таблицы transactions...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'transactions' AND column_name = 'type'
        """)
        
        if cur.fetchone():
            print("✅ Колонка 'type' уже существует")
            return True
        
        # Добавляем колонку 'type'
        print("➕ Добавляем колонку 'type' в таблицу transactions...")
        cur.execute("""
            ALTER TABLE transactions 
            ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'spend'
        """)
        
        # Обновляем существующие записи
        print("🔄 Обновляем существующие записи...")
        cur.execute("""
            UPDATE transactions 
            SET type = 'spend' 
            WHERE type IS NULL OR type = ''
        """)
        
        # Применяем изменения
        conn.commit()
        print("✅ Колонка 'type' успешно добавлена в таблицу transactions")
        
        # Проверяем результат
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'transactions' 
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("\n📋 Структура таблицы transactions:")
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
    print("🚀 Исправление таблицы transactions...")
    success = fix_transactions_table()
    if success:
        print("✅ Исправление завершено успешно!")
        sys.exit(0)
    else:
        print("❌ Исправление не удалось!")
        sys.exit(1)
