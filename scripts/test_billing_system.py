#!/usr/bin/env python3
"""
Комплексный тест системы биллинга и аудита
"""
import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_balance_manager():
    """Тест balance_manager"""
    print("🧪 Тестирование balance_manager...")
    
    try:
        from app.services import balance_manager
        
        test_user_id = 5015100177
        
        # Тест получения баланса
        balance = balance_manager.get_balance(test_user_id)
        print(f"✅ get_balance: {balance}")
        
        # Тест добавления монет
        new_balance = balance_manager.add_coins(
            user_id=test_user_id,
            amount=10,
            reason="Test add coins",
            feature="test_add"
        )
        print(f"✅ add_coins: {new_balance}")
        
        # Тест списания монет
        final_balance = balance_manager.spend_coins(
            user_id=test_user_id,
            amount=5,
            reason="Test spend coins",
            feature="test_spend"
        )
        print(f"✅ spend_coins: {final_balance}")
        
        # Тест проверки достаточности средств
        can_afford = balance_manager.can_afford(test_user_id, 1000)
        print(f"✅ can_afford(1000): {can_afford}")
        
        # Тест получения сводки
        summary = balance_manager.get_user_summary(test_user_id)
        print(f"✅ get_user_summary: {len(summary['recent_transactions'])} transactions")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в balance_manager: {e}")
        return False

def test_billing_observer():
    """Тест billing_observer"""
    print("\n🧪 Тестирование billing_observer...")
    
    try:
        from app.services import billing_observer
        
        test_user_id = 5015100177
        
        # Тест получения истории
        history = billing_observer.get_user_recent_transactions(test_user_id, 5)
        print(f"✅ get_user_recent_transactions: {len(history)} records")
        
        # Тест ежедневного отчета
        daily_report = billing_observer.get_daily_report()
        print(f"✅ get_daily_report: {daily_report['total_spent']} spent, {daily_report['total_earned']} earned")
        
        # Тест недельного отчета
        weekly_report = billing_observer.get_weekly_report()
        print(f"✅ get_weekly_report: {weekly_report['unique_users']} users")
        
        # Тест месячного отчета
        monthly_report = billing_observer.get_monthly_report()
        print(f"✅ get_monthly_report: {monthly_report['unique_users']} users")
        
        # Тест форматирования отчета
        formatted = billing_observer.format_report(daily_report)
        print(f"✅ format_report: {len(formatted)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в billing_observer: {e}")
        return False

def test_audit_database():
    """Тест базы данных аудита"""
    print("\n🧪 Тестирование базы данных аудита...")
    
    try:
        from app.db import db_billing_audit
        
        # Инициализация таблицы
        db_billing_audit.init_audit_table()
        print("✅ init_audit_table")
        
        # Тест вставки записи
        test_record = {
            "user_id": 999999,
            "delta": 10,
            "feature": "test_feature",
            "reason": "Test record",
            "old_balance": 100,
            "new_balance": 110,
            "timestamp": "2025-01-01 12:00:00"
        }
        
        success = db_billing_audit.insert_record(test_record)
        print(f"✅ insert_record: {success}")
        
        # Тест получения истории
        history = db_billing_audit.get_user_history(999999, 5)
        print(f"✅ get_user_history: {len(history)} records")
        
        # Тест ежедневного отчета
        from datetime import date
        daily_report = db_billing_audit.get_daily_report(date.today())
        print(f"✅ get_daily_report: {daily_report['total_spent']} spent")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в базе данных аудита: {e}")
        return False

def test_pricing_system():
    """Тест системы ценообразования"""
    print("\n🧪 Тестирование системы ценообразования...")
    
    try:
        from app.config.pricing import FEATURE_COSTS, FEATURE_DESCRIPTIONS, FEATURE_CATEGORIES
        
        # Тест получения стоимости
        video_cost = FEATURE_COSTS.get("video_8s_audio", 0)
        print(f"✅ FEATURE_COSTS: video_8s_audio = {video_cost}")
        
        # Тест описаний
        video_desc = FEATURE_DESCRIPTIONS.get("video_8s_audio", "Unknown")
        print(f"✅ FEATURE_DESCRIPTIONS: video_8s_audio = {video_desc}")
        
        # Тест категорий
        video_category = None
        for category, features in FEATURE_CATEGORIES.items():
            if "video_8s_audio" in features:
                video_category = category
                break
        print(f"✅ FEATURE_CATEGORIES: video_8s_audio in {video_category}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в системе ценообразования: {e}")
        return False

def main():
    print("🚀 Комплексный тест системы биллинга и аудита\n")
    
    tests = [
        test_balance_manager,
        test_billing_observer,
        test_audit_database,
        test_pricing_system
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test.__name__}: {e}")
            results.append(False)
    
    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Успешных тестов: {sum(results)}")
    print(f"❌ Неудачных тестов: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 Все тесты прошли успешно!")
        print("💡 Система биллинга и аудита готова к работе")
        return True
    else:
        print("\n💥 Некоторые тесты не прошли!")
        print("🔧 Проверьте логи и исправьте ошибки")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
