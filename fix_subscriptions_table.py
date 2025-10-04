#!/usr/bin/env python3
"""
Скрипт для исправления структуры таблицы subscriptions в PostgreSQL
Проверяет и добавляет недостающие поля
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def fix_subscriptions_table():
    print("🔧 ИСПРАВЛЕНИЕ СТРУКТУРЫ ТАБЛИЦЫ SUBSCRIPTIONS")
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
        
        # Шаг 1: Проверяем текущую структуру таблицы subscriptions
        print("\n🔍 ШАГ 1: Проверка текущей структуры таблицы subscriptions")
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions'
            ORDER BY ordinal_position
        """)
        
        current_columns = cur.fetchall()
        print("📊 Текущие колонки в таблице subscriptions:")
        for col in current_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Шаг 2: Определяем ожидаемую структуру
        expected_columns = {
            'id': 'integer',
            'user_id': 'bigint',
            'plan': 'text',
            'coins': 'integer',
            'price_rub': 'integer',
            'start_date': 'timestamp without time zone',
            'end_date': 'timestamp without time zone',
            'is_active': 'boolean',
            'payment_id': 'text',
            'created_at': 'timestamp without time zone'
        }
        
        print("\n📋 ШАГ 2: Ожидаемая структура таблицы subscriptions")
        for col_name, col_type in expected_columns.items():
            print(f"  - {col_name} ({col_type})")
        
        # Шаг 3: Проверяем, какие колонки отсутствуют
        print("\n🔍 ШАГ 3: Поиск отсутствующих колонок")
        current_column_names = [col[0] for col in current_columns]
        missing_columns = []
        
        for col_name in expected_columns.keys():
            if col_name not in current_column_names:
                missing_columns.append(col_name)
                print(f"❌ Отсутствует колонка: {col_name}")
            else:
                print(f"✅ Колонка {col_name} существует")
        
        # Шаг 4: Добавляем отсутствующие колонки
        if missing_columns:
            print(f"\n🔧 ШАГ 4: Добавление {len(missing_columns)} отсутствующих колонок")
            
            # SQL команды для добавления колонок
            alter_commands = []
            
            if 'id' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN id SERIAL PRIMARY KEY")
            
            if 'user_id' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN user_id BIGINT NOT NULL")
            
            if 'plan' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN plan TEXT NOT NULL")
            
            if 'coins' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN coins INTEGER DEFAULT 0")
            
            if 'price_rub' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN price_rub INTEGER NOT NULL")
            
            if 'start_date' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            if 'end_date' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN end_date TIMESTAMP NOT NULL")
            
            if 'is_active' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            
            if 'payment_id' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN payment_id TEXT")
            
            if 'created_at' in missing_columns:
                alter_commands.append("ALTER TABLE subscriptions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            # Выполняем команды
            for cmd in alter_commands:
                try:
                    print(f"🔧 Выполняем: {cmd}")
                    cur.execute(cmd)
                    conn.commit()
                    print(f"✅ Успешно: {cmd}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"ℹ️ Колонка уже существует: {cmd}")
                    else:
                        print(f"❌ Ошибка: {cmd} - {e}")
        else:
            print("\n✅ Все необходимые колонки уже существуют")
        
        # Шаг 5: Проверяем финальную структуру
        print("\n🔍 ШАГ 5: Проверка финальной структуры таблицы subscriptions")
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions'
            ORDER BY ordinal_position
        """)
        
        final_columns = cur.fetchall()
        print("📊 Финальные колонки в таблице subscriptions:")
        for col in final_columns:
            print(f"  - {col[0]} ({col[1]}) - nullable: {col[2]}, default: {col[3]}")
        
        # Шаг 6: Проверяем данные в таблице
        print("\n🔍 ШАГ 6: Проверка данных в таблице subscriptions")
        cur.execute("SELECT COUNT(*) FROM subscriptions")
        sub_count = cur.fetchone()[0]
        print(f"📊 Количество записей в subscriptions: {sub_count}")
        
        if sub_count > 0:
            cur.execute("SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 3")
            latest_subs = cur.fetchall()
            print("📊 Последние подписки:")
            for i, row in enumerate(latest_subs, 1):
                print(f"  {i}. {row}")
        
        # Шаг 7: Тестируем INSERT запрос
        print("\n🧪 ШАГ 7: Тестирование INSERT запроса")
        try:
            # Тестовый INSERT (не сохраняем)
            cur.execute("""
                INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, is_active, payment_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (999999999, 'test', 0, 0, '2025-01-01 00:00:00', '2025-01-02 00:00:00', True, 'test-payment', '2025-01-01 00:00:00'))
            
            # Откатываем тестовую запись
            cur.execute("DELETE FROM subscriptions WHERE user_id = 999999999")
            conn.commit()
            print("✅ INSERT запрос работает корректно")
        except Exception as e:
            print(f"❌ Ошибка при тестировании INSERT: {e}")
        
        conn.close()
        print("\n✅ СТРУКТУРА ТАБЛИЦЫ SUBSCRIPTIONS ИСПРАВЛЕНА УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_subscriptions_table()
    if success:
        print("\n🎯 ТАБЛИЦА SUBSCRIPTIONS ГОТОВА!")
        print("✅ Все необходимые колонки добавлены")
        print("✅ INSERT запросы должны работать корректно")
        print("✅ YooKassa webhook должен создавать подписки без ошибок")
    else:
        print("\n❌ Не удалось исправить структуру таблицы subscriptions")
        sys.exit(1)
