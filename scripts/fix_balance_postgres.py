#!/usr/bin/env python3
"""
Скрипт для исправления баланса пользователя в PostgreSQL Railway
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_balance_postgres():
    """Исправить баланс в PostgreSQL Railway"""
    print("🔧 Исправление баланса в PostgreSQL Railway...")
    
    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ DATABASE_URL не найден в переменных окружения")
        print("💡 Выполните скрипт в Railway Shell для доступа к переменным окружения")
        return False
    
    print(f"📊 DATABASE_URL: {database_url[:20]}...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        UID = 5015100177
        TARGET = 100
        
        # Получаем текущий баланс
        cur.execute("SELECT coins FROM users WHERE user_id = %s", (UID,))
        result = cur.fetchone()
        
        if not result:
            print(f"❌ Пользователь {UID} не найден в базе данных")
            return False
        
        old_balance = result[0]
        print(f"💰 Текущий баланс: {old_balance}")
        
        # Вычисляем дельту
        delta = TARGET - old_balance
        print(f"📈 Дельта: {delta}")
        
        # Обновляем баланс
        cur.execute("UPDATE users SET coins = %s WHERE user_id = %s", (TARGET, UID))
        
        # Добавляем запись в транзакции
        cur.execute("""
            INSERT INTO transactions(user_id, feature, coins_spent, note)
            VALUES (%s, 'balance_update', 0, %s)
        """, (UID, f"Admin set balance to {TARGET} (was {old_balance})"))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Баланс обновлён: old={old_balance}, new={TARGET}, delta={delta}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Исправление баланса пользователя 5015100177 = 100 монет в PostgreSQL\n")
    
    if fix_balance_postgres():
        print("\n🎉 Баланс успешно обновлен в Railway PostgreSQL!")
        print("💡 Теперь в логах бота должно появиться: Loaded user ... coins=100")
        return 0
    else:
        print("\n❌ Не удалось обновить баланс")
        return 1

if __name__ == "__main__":
    exit(main())
