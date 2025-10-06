#!/usr/bin/env python3
"""
Скрипт для генерации ежедневного отчета по биллингу
"""
import os
import sys
from datetime import date

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("📊 Генерация ежедневного отчета по биллингу...")
    
    try:
        from app.services import billing_observer
        
        # Получаем отчет за сегодня
        report = billing_observer.get_daily_report()
        
        # Форматируем отчет
        formatted_report = billing_observer.format_report(report)
        
        print("=" * 50)
        print(formatted_report)
        print("=" * 50)
        
        # Дополнительная статистика
        print(f"\n📈 Дополнительная статистика:")
        print(f"• Средний расход на пользователя: {report['total_spent'] / max(report['unique_users'], 1):.1f} монет")
        print(f"• Эффективность пополнений: {report['total_earned'] / max(report['total_spent'], 1):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчета: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
