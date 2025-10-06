#!/usr/bin/env python3
"""
Финальный скрипт для исправления баланса в PostgreSQL Railway
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🚀 Финальное исправление баланса в PostgreSQL Railway...")
    
    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
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
        
        # Проверяем результат
        from app.db import db_subscriptions as db
        new_balance = db.get_user_balance(UID)
        print(f"🔍 Проверка через db_subscriptions: {new_balance}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Баланс успешно исправлен!")
        print("💡 Теперь в логах бота должно появиться: Loaded user ... coins=100")
    else:
        print("\n❌ Не удалось исправить баланс")
    exit(0 if success else 1)
