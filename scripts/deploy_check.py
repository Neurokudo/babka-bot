#!/usr/bin/env python3
"""
Скрипт для проверки деплоя и подключения к БД
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔍 Checking deployment and database connection...")
    
    # Проверяем переменные окружения
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:20]}...")
    
    # Проверяем подключение к БД
    try:
        from app.db import db_subscriptions as db
        
        uid = 5015100177
        balance = db.get_user_balance(uid)
        print(f"✅ Connected to DB, user {uid} balance: {balance}")
        
        # Проверяем функции pricing
        from app.services.pricing import get_available_tariffs, format_plans_list
        
        tariffs = get_available_tariffs()
        print(f"✅ Pricing service working, {len(tariffs)} tariffs available")
        
        plans_text = format_plans_list()
        print(f"✅ Plans text generated, length: {len(plans_text)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ All checks passed!' if success else '❌ Some checks failed!'}")
    exit(0 if success else 1)
