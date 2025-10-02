# -*- coding: utf-8 -*-
"""
app/utils/cron.py - Фоновые задачи и cron-функции
"""

import logging
from datetime import datetime, timezone
from typing import List

from app.db.queries import db
from app.billing.plans import check_and_reset_expired_plans
from app.billing.coins import get_balance
from app.utils.env import config

log = logging.getLogger("cron")


def check_expired_plans() -> List[int]:
    """
    Проверяет и сбрасывает истекшие планы
    
    Returns:
        Список ID пользователей, у которых был сброшен план
    """
    log.info("Checking expired plans...")
    
    try:
        reset_users = check_and_reset_expired_plans()
        
        if reset_users:
            log.info(f"Reset expired plans for {len(reset_users)} users: {reset_users}")
        else:
            log.info("No expired plans found")
        
        return reset_users
        
    except Exception as e:
        log.error(f"Failed to check expired plans: {e}")
        return []


def check_low_balance_users() -> List[int]:
    """
    Находит пользователей с низким балансом
    
    Returns:
        Список ID пользователей с балансом < LOW_COINS_THRESHOLD
    """
    log.info("Checking users with low balance...")
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id FROM users 
                WHERE coins < %s 
                AND user_id != %s
                ORDER BY coins ASC
                """,
                (15, config.ADMIN_ID)  # LOW_COINS_THRESHOLD из config
            )
            results = cursor.fetchall()
            low_balance_users = [row[0] for row in results]
            
            if low_balance_users:
                log.info(f"Found {len(low_balance_users)} users with low balance: {low_balance_users}")
            else:
                log.info("No users with low balance found")
            
            return low_balance_users
            
    except Exception as e:
        log.error(f"Failed to check low balance users: {e}")
        return []


def cleanup_old_jobs(days_old: int = 30) -> int:
    """
    Удаляет старые завершенные задачи
    
    Args:
        days_old: Возраст задач в днях
    
    Returns:
        Количество удаленных задач
    """
    log.info(f"Cleaning up jobs older than {days_old} days...")
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM jobs 
                WHERE status IN ('succeeded', 'failed') 
                AND created_at < NOW() - INTERVAL '%s days'
                """,
                (days_old,)
            )
            
            deleted_count = cursor.rowcount
            log.info(f"Deleted {deleted_count} old jobs")
            return deleted_count
            
    except Exception as e:
        log.error(f"Failed to cleanup old jobs: {e}")
        return 0


def cleanup_old_transactions(days_old: int = 90) -> int:
    """
    Удаляет старые транзакции (только для аудита)
    
    Args:
        days_old: Возраст транзакций в днях
    
    Returns:
        Количество удаленных транзакций
    """
    log.info(f"Cleaning up transactions older than {days_old} days...")
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM transactions 
                WHERE created_at < NOW() - INTERVAL '%s days'
                """,
                (days_old,)
            )
            
            deleted_count = cursor.rowcount
            log.info(f"Deleted {deleted_count} old transactions")
            return deleted_count
            
    except Exception as e:
        log.error(f"Failed to cleanup old transactions: {e}")
        return 0


def cleanup_old_support_reports(days_old: int = 180) -> int:
    """
    Удаляет старые репорты поддержки
    
    Args:
        days_old: Возраст репортов в днях
    
    Returns:
        Количество удаленных репортов
    """
    log.info(f"Cleaning up support reports older than {days_old} days...")
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM support_reports 
                WHERE created_at < NOW() - INTERVAL '%s days'
                """,
                (days_old,)
            )
            
            deleted_count = cursor.rowcount
            log.info(f"Deleted {deleted_count} old support reports")
            return deleted_count
            
    except Exception as e:
        log.error(f"Failed to cleanup old support reports: {e}")
        return 0


def run_daily_maintenance() -> dict:
    """
    Выполняет ежедневное обслуживание
    
    Returns:
        Словарь с результатами выполнения задач
    """
    log.info("Starting daily maintenance...")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "expired_plans_reset": 0,
        "low_balance_users": 0,
        "old_jobs_cleaned": 0,
        "old_transactions_cleaned": 0,
        "old_reports_cleaned": 0,
        "errors": []
    }
    
    try:
        # Проверяем истекшие планы
        reset_users = check_expired_plans()
        results["expired_plans_reset"] = len(reset_users)
        
        # Проверяем пользователей с низким балансом
        low_balance_users = check_low_balance_users()
        results["low_balance_users"] = len(low_balance_users)
        
        # Очищаем старые данные
        results["old_jobs_cleaned"] = cleanup_old_jobs()
        results["old_transactions_cleaned"] = cleanup_old_transactions()
        results["old_reports_cleaned"] = cleanup_old_support_reports()
        
        log.info(f"Daily maintenance completed: {results}")
        
    except Exception as e:
        error_msg = f"Daily maintenance failed: {e}"
        log.error(error_msg)
        results["errors"].append(error_msg)
    
    return results


def get_system_stats() -> dict:
    """
    Получает статистику системы
    
    Returns:
        Словарь со статистикой
    """
    try:
        with db.connection.cursor() as cursor:
            # Общая статистика пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE coins > 0")
            active_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(coins) FROM users")
            total_coins = cursor.fetchone()[0] or 0
            
            # Статистика планов
            cursor.execute("SELECT plan, COUNT(*) FROM users GROUP BY plan")
            plan_stats = dict(cursor.fetchall())
            
            # Статистика транзакций за последние 24 часа
            cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE created_at > NOW() - INTERVAL '24 hours'"
            )
            transactions_24h = cursor.fetchone()[0]
            
            # Статистика задач
            cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
            job_stats = dict(cursor.fetchall())
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_coins": total_coins,
                "plan_distribution": plan_stats,
                "transactions_24h": transactions_24h,
                "job_stats": job_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        log.error(f"Failed to get system stats: {e}")
        return {"error": str(e)}
