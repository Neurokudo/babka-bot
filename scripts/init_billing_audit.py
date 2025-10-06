#!/usr/bin/env python3
"""
Скрипт для инициализации таблицы аудита биллинга
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔧 Инициализация таблицы аудита биллинга...")
    
    try:
        from app.db import db_billing_audit
        
        # Инициализируем таблицу
        db_billing_audit.init_audit_table()
        
        print("✅ Таблица billing_audit успешно создана")
        print("📊 Индексы созданы для быстрого поиска")
        print("🎯 Система аудита готова к работе")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
