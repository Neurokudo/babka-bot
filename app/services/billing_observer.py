"""
Модуль наблюдения и логирования всех транзакций
Фиксирует каждое изменение баланса в журнале billing_audit
"""

from app.db import db_billing_audit
import datetime
import logging
from typing import List, Dict, Any, Optional

log = logging.getLogger("babka-bot")

def log(user_id: int, delta: int, feature: str, reason: str, old_balance: int, new_balance: int) -> bool:
    """
    Записать операцию в журнал аудита
    
    Args:
        user_id: ID пользователя
        delta: Изменение баланса (положительное для пополнения, отрицательное для списания)
        feature: Тип функции/операции
        reason: Причина операции
        old_balance: Баланс до операции
        new_balance: Баланс после операции
    
    Returns:
        True если запись успешна, False иначе
    """
    try:
        record = {
            "user_id": user_id,
            "delta": delta,
            "feature": feature,
            "reason": reason,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "timestamp": datetime.datetime.now()
        }
        
        success = db_billing_audit.insert_record(record)
        
        if success:
            log.info(f"[AUDIT] {user_id} | Δ={delta:+d} | {feature or 'unknown'} | {old_balance}→{new_balance} | {reason}")
        else:
            log.error(f"[AUDIT FAILED] {user_id} | Δ={delta:+d} | {feature or 'unknown'}")
        
        return success
        
    except Exception as e:
        log.error(f"Failed to log billing operation for user {user_id}: {e}")
        return False

def get_user_recent_transactions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получить последние транзакции пользователя
    
    Args:
        user_id: ID пользователя
        limit: Количество записей
    
    Returns:
        Список транзакций
    """
    try:
        return db_billing_audit.get_user_history(user_id, limit)
    except Exception as e:
        log.error(f"Failed to get user transactions for {user_id}: {e}")
        return []

def get_daily_report(date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Получить ежедневный отчет по операциям
    
    Args:
        date: Дата отчета (по умолчанию сегодня)
    
    Returns:
        Словарь с отчетом
    """
    try:
        if date is None:
            date = datetime.date.today()
        
        return db_billing_audit.get_daily_report(date)
    except Exception as e:
        log.error(f"Failed to get daily report for {date}: {e}")
        return {
            "date": date,
            "total_spent": 0,
            "total_earned": 0,
            "unique_users": 0,
            "top_features": []
        }

def get_weekly_report(week_start: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Получить недельный отчет по операциям
    
    Args:
        week_start: Начало недели (по умолчанию начало текущей недели)
    
    Returns:
        Словарь с отчетом
    """
    try:
        if week_start is None:
            today = datetime.date.today()
            week_start = today - datetime.timedelta(days=today.weekday())
        
        week_end = week_start + datetime.timedelta(days=6)
        
        return db_billing_audit.get_period_report(week_start, week_end)
    except Exception as e:
        log.error(f"Failed to get weekly report for {week_start}: {e}")
        return {
            "period_start": week_start,
            "period_end": week_end,
            "total_spent": 0,
            "total_earned": 0,
            "unique_users": 0,
            "top_features": []
        }

def get_monthly_report(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Получить месячный отчет по операциям
    
    Args:
        month: Месяц (по умолчанию текущий)
        year: Год (по умолчанию текущий)
    
    Returns:
        Словарь с отчетом
    """
    try:
        if month is None or year is None:
            now = datetime.date.today()
            month = month or now.month
            year = year or now.year
        
        month_start = datetime.date(year, month, 1)
        if month == 12:
            month_end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            month_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        return db_billing_audit.get_period_report(month_start, month_end)
    except Exception as e:
        log.error(f"Failed to get monthly report for {year}-{month:02d}: {e}")
        return {
            "period_start": month_start,
            "period_end": month_end,
            "total_spent": 0,
            "total_earned": 0,
            "unique_users": 0,
            "top_features": []
        }

def get_feature_statistics(feature: str, days: int = 30) -> Dict[str, Any]:
    """
    Получить статистику по конкретной функции
    
    Args:
        feature: Название функции
        days: Количество дней для анализа
    
    Returns:
        Словарь со статистикой
    """
    try:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        return db_billing_audit.get_feature_statistics(feature, start_date, end_date)
    except Exception as e:
        log.error(f"Failed to get feature statistics for {feature}: {e}")
        return {
            "feature": feature,
            "period_days": days,
            "total_usage": 0,
            "total_cost": 0,
            "unique_users": 0
        }

def format_report(report: Dict[str, Any]) -> str:
    """
    Форматировать отчет в читаемый вид
    
    Args:
        report: Словарь с отчетом
    
    Returns:
        Отформатированная строка
    """
    try:
        if "date" in report:
            # Ежедневный отчет
            date_str = report["date"].strftime("%Y-%m-%d")
            return f"""📅 Ежедневный отчёт BabkaBot ({date_str})
💸 Списаний за сутки: {report.get('total_spent', 0)} монет
💰 Начислений за сутки: {report.get('total_earned', 0)} монет
👥 Уникальных пользователей: {report.get('unique_users', 0)}
🔥 Топ функций:
{_format_top_features(report.get('top_features', []))}"""
        
        elif "period_start" in report:
            # Периодический отчет
            start_str = report["period_start"].strftime("%Y-%m-%d")
            end_str = report["period_end"].strftime("%Y-%m-%d")
            return f"""📊 Отчёт BabkaBot ({start_str} - {end_str})
💸 Списаний за период: {report.get('total_spent', 0)} монет
💰 Начислений за период: {report.get('total_earned', 0)} монет
👥 Уникальных пользователей: {report.get('unique_users', 0)}
🔥 Топ функций:
{_format_top_features(report.get('top_features', []))}"""
        
        else:
            return f"📊 Отчёт BabkaBot\n{report}"
    
    except Exception as e:
        log.error(f"Failed to format report: {e}")
        return f"❌ Ошибка форматирования отчета: {e}"

def _format_top_features(features: List[Dict[str, Any]], limit: int = 5) -> str:
    """Форматировать топ функций"""
    if not features:
        return "   Нет данных"
    
    lines = []
    for i, feature in enumerate(features[:limit], 1):
        name = feature.get('feature', 'unknown')
        cost = feature.get('total_cost', 0)
        count = feature.get('usage_count', 0)
        lines.append(f"   {i}. {name} — {cost} монет ({count} использований)")
    
    return "\n".join(lines)
