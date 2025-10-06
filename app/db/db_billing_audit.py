"""
Модуль для работы с таблицей аудита биллинга
Содержит функции для записи и получения данных о всех операциях с монетами
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date

log = logging.getLogger("db_billing_audit")

def db_conn():
    """Получить соединение с базой данных"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url and database_url.startswith("postgresql://"):
        # PostgreSQL для Railway
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(database_url)
            return conn
        except Exception as e:
            log.warning(f"PostgreSQL connection failed: {e}, falling back to SQLite")
    
    # SQLite для локальной разработки
    db_path = os.getenv("DATABASE_URL", "sqlite:///./babka_bot.db").replace("sqlite:///", "")
    return sqlite3.connect(db_path)

def init_audit_table():
    """Инициализация таблицы аудита биллинга"""
    with db_conn() as conn:
        cur = conn.cursor()
        
        # Определяем тип базы данных
        database_url = os.getenv("DATABASE_URL", "")
        is_postgres = database_url.startswith("postgresql://")
        
        if is_postgres:
            # PostgreSQL синтаксис для Railway
            cur.execute("""
                CREATE TABLE IF NOT EXISTS billing_audit (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    delta INTEGER NOT NULL,
                    feature TEXT,
                    reason TEXT,
                    old_balance INTEGER,
                    new_balance INTEGER,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Создаем индексы для быстрого поиска
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_user_id 
                ON billing_audit(user_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_timestamp 
                ON billing_audit(timestamp)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_feature 
                ON billing_audit(feature)
            """)
            
        else:
            # SQLite синтаксис для локальной разработки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS billing_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    delta INTEGER NOT NULL,
                    feature TEXT,
                    reason TEXT,
                    old_balance INTEGER,
                    new_balance INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создаем индексы для быстрого поиска
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_user_id 
                ON billing_audit(user_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_timestamp 
                ON billing_audit(timestamp)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_audit_feature 
                ON billing_audit(feature)
            """)
        
        conn.commit()
        log.info("Billing audit table initialized successfully")

def insert_record(record: Dict[str, Any]) -> bool:
    """
    Вставить запись в таблицу аудита
    
    Args:
        record: Словарь с данными записи
    
    Returns:
        True если успешно, False иначе
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            query = """
                INSERT INTO billing_audit
                (user_id, delta, feature, reason, old_balance, new_balance, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                record["user_id"],
                record["delta"],
                record["feature"],
                record["reason"],
                record["old_balance"],
                record["new_balance"],
                record["timestamp"]
            )
            
            cur.execute(query, params)
            conn.commit()
            
            log.debug(f"Billing audit record inserted for user {record['user_id']}")
            return True
            
    except Exception as e:
        log.error(f"Failed to insert billing audit record: {e}")
        return False

def get_user_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получить историю операций пользователя
    
    Args:
        user_id: ID пользователя
        limit: Количество записей
    
    Returns:
        Список записей
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            query = """
                SELECT id, user_id, delta, feature, reason, old_balance, new_balance, timestamp
                FROM billing_audit 
                WHERE user_id = %s 
                ORDER BY id DESC 
                LIMIT %s
            """
            
            cur.execute(query, (user_id, limit))
            
            # Получаем результаты в виде словарей
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
    except Exception as e:
        log.error(f"Failed to get user history for {user_id}: {e}")
        return []

def get_daily_report(report_date: date) -> Dict[str, Any]:
    """
    Получить ежедневный отчет
    
    Args:
        report_date: Дата отчета
    
    Returns:
        Словарь с отчетом
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Общая статистика
            cur.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN delta < 0 THEN ABS(delta) ELSE 0 END), 0) as total_spent,
                    COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) as total_earned,
                    COUNT(DISTINCT user_id) as unique_users
                FROM billing_audit 
                WHERE DATE(timestamp) = %s
            """, (report_date,))
            
            stats = cur.fetchone()
            
            # Топ функций
            cur.execute("""
                SELECT 
                    feature,
                    COUNT(*) as usage_count,
                    SUM(ABS(delta)) as total_cost
                FROM billing_audit 
                WHERE DATE(timestamp) = %s AND delta < 0
                GROUP BY feature
                ORDER BY total_cost DESC
                LIMIT 10
            """, (report_date,))
            
            top_features = []
            for row in cur.fetchall():
                top_features.append({
                    "feature": row[0] or "unknown",
                    "usage_count": row[1],
                    "total_cost": row[2]
                })
            
            return {
                "date": report_date,
                "total_spent": stats[0] if stats else 0,
                "total_earned": stats[1] if stats else 0,
                "unique_users": stats[2] if stats else 0,
                "top_features": top_features
            }
            
    except Exception as e:
        log.error(f"Failed to get daily report for {report_date}: {e}")
        return {
            "date": report_date,
            "total_spent": 0,
            "total_earned": 0,
            "unique_users": 0,
            "top_features": []
        }

def get_period_report(start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Получить отчет за период
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Словарь с отчетом
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Общая статистика
            cur.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN delta < 0 THEN ABS(delta) ELSE 0 END), 0) as total_spent,
                    COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) as total_earned,
                    COUNT(DISTINCT user_id) as unique_users
                FROM billing_audit 
                WHERE DATE(timestamp) BETWEEN %s AND %s
            """, (start_date, end_date))
            
            stats = cur.fetchone()
            
            # Топ функций
            cur.execute("""
                SELECT 
                    feature,
                    COUNT(*) as usage_count,
                    SUM(ABS(delta)) as total_cost
                FROM billing_audit 
                WHERE DATE(timestamp) BETWEEN %s AND %s AND delta < 0
                GROUP BY feature
                ORDER BY total_cost DESC
                LIMIT 10
            """, (start_date, end_date))
            
            top_features = []
            for row in cur.fetchall():
                top_features.append({
                    "feature": row[0] or "unknown",
                    "usage_count": row[1],
                    "total_cost": row[2]
                })
            
            return {
                "period_start": start_date,
                "period_end": end_date,
                "total_spent": stats[0] if stats else 0,
                "total_earned": stats[1] if stats else 0,
                "unique_users": stats[2] if stats else 0,
                "top_features": top_features
            }
            
    except Exception as e:
        log.error(f"Failed to get period report for {start_date} - {end_date}: {e}")
        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_spent": 0,
            "total_earned": 0,
            "unique_users": 0,
            "top_features": []
        }

def get_feature_statistics(feature: str, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Получить статистику по конкретной функции
    
    Args:
        feature: Название функции
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Словарь со статистикой
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total_usage,
                    SUM(ABS(delta)) as total_cost,
                    COUNT(DISTINCT user_id) as unique_users
                FROM billing_audit 
                WHERE feature = %s 
                AND DATE(timestamp) BETWEEN %s AND %s
                AND delta < 0
            """, (feature, start_date, end_date))
            
            stats = cur.fetchone()
            
            return {
                "feature": feature,
                "period_start": start_date,
                "period_end": end_date,
                "total_usage": stats[0] if stats else 0,
                "total_cost": stats[1] if stats else 0,
                "unique_users": stats[2] if stats else 0
            }
            
    except Exception as e:
        log.error(f"Failed to get feature statistics for {feature}: {e}")
        return {
            "feature": feature,
            "period_start": start_date,
            "period_end": end_date,
            "total_usage": 0,
            "total_cost": 0,
            "unique_users": 0
        }

def cleanup_old_records(days_to_keep: int = 90) -> int:
    """
    Удалить старые записи аудита
    
    Args:
        days_to_keep: Количество дней для хранения
    
    Returns:
        Количество удаленных записей
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            cutoff_date = datetime.now().date() - datetime.timedelta(days=days_to_keep)
            
            cur.execute("""
                DELETE FROM billing_audit 
                WHERE DATE(timestamp) < %s
            """, (cutoff_date,))
            
            deleted_count = cur.rowcount
            conn.commit()
            
            log.info(f"Cleaned up {deleted_count} old billing audit records")
            return deleted_count
            
    except Exception as e:
        log.error(f"Failed to cleanup old records: {e}")
        return 0
