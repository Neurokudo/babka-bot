#!/usr/bin/env python3
"""
Скрипт для миграции всех операций с монетами на balance_manager
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔄 Миграция операций с монетами на balance_manager...")
    
    try:
        # Инициализируем таблицу аудита
        from app.db import db_billing_audit
        db_billing_audit.init_audit_table()
        print("✅ Таблица аудита инициализирована")
        
        # Тестируем balance_manager
        from app.services import balance_manager, billing_observer
        
        # Тестовый пользователь
        test_user_id = 5015100177
        
        print(f"🧪 Тестирование с пользователем {test_user_id}...")
        
        # Получаем текущий баланс
        current_balance = balance_manager.get_balance(test_user_id)
        print(f"💰 Текущий баланс: {current_balance}")
        
        # Тестируем добавление монет
        print("➕ Тестируем добавление монет...")
        new_balance = balance_manager.add_coins(
            user_id=test_user_id,
            amount=10,
            reason="Migration test",
            feature="admin_test"
        )
        print(f"✅ Баланс после добавления: {new_balance}")
        
        # Тестируем списание монет
        print("➖ Тестируем списание монет...")
        final_balance = balance_manager.spend_coins(
            user_id=test_user_id,
            amount=5,
            reason="Migration test spend",
            feature="admin_test"
        )
        print(f"✅ Баланс после списания: {final_balance}")
        
        # Тестируем получение истории
        print("📋 Тестируем получение истории...")
        history = billing_observer.get_user_recent_transactions(test_user_id, 5)
        print(f"✅ Получено {len(history)} записей истории")
        
        # Тестируем ежедневный отчет
        print("📊 Тестируем ежедневный отчет...")
        daily_report = billing_observer.get_daily_report()
        print(f"✅ Ежедневный отчет: {daily_report['total_spent']} потрачено, {daily_report['total_earned']} заработано")
        
        print("\n🎉 Миграция завершена успешно!")
        print("💡 Теперь все операции с монетами должны использовать balance_manager")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
