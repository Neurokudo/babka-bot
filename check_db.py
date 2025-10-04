#!/usr/bin/env python3
"""
Скрипт для проверки подключения к базе данных
"""

import os
import sys
from dotenv import load_dotenv

def check_database():
    """Проверить подключение к базе данных"""
    load_dotenv()
    
    print("🔍 Проверка конфигурации базы данных...")
    
    # Проверяем переменные окружения
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print(f"✅ DATABASE_URL найден: {database_url[:50]}...")
    else:
        print("⚠️  DATABASE_URL не найден, будет использована SQLite")
    
    # Проверяем подключение к БД
    try:
        from app.db.queries import db_manager
        
        print("🔌 Попытка подключения к базе данных...")
        db_manager._init_db()
        
        if db_manager._initialized:
            print("✅ База данных подключена успешно!")
            
            # Тестируем создание пользователя
            test_user = db_manager.create_user(999999, "test_user")
            print(f"✅ Тестовый пользователь создан: {test_user.username}")
            
            # Тестируем получение пользователя
            user = db_manager.get_user(999999)
            if user:
                print(f"✅ Пользователь найден: баланс {user.balance} монет")
            else:
                print("❌ Пользователь не найден")
                
        else:
            print("⚠️  База данных недоступна, работаем в режиме заглушек")
            
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        print("⚠️  Бот будет работать в режиме заглушек")
    
    print("\n📋 Рекомендации:")
    print("1. Убедитесь, что на Railway настроена PostgreSQL база данных")
    print("2. Проверьте переменную окружения DATABASE_URL")
    print("3. Бот может работать без БД в режиме заглушек для тестирования")

if __name__ == "__main__":
    check_database()
