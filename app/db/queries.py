# -*- coding: utf-8 -*-
"""
app/db/queries.py - Подготовленные SQL запросы и подключение к БД
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logging.getLogger("db.queries").warning(
        "psycopg2 not installed. Database features disabled."
    )

log = logging.getLogger("db.queries")
DATABASE_URL = os.getenv("DATABASE_URL")


class Database:
    def __init__(self) -> None:
        self.connection = None
        if PSYCOPG2_AVAILABLE:
            self.connect()

    def connect(self) -> None:
        """Подключается к базе данных"""
        if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
            log.warning("DATABASE_URL not set, database features disabled")
            return
        
        try:
            self.connection = psycopg2.connect(DATABASE_URL)
            log.info("Connected to PostgreSQL database")
        except Exception as exc:
            log.error(f"Failed to connect to database: {exc}")
            self.connection = None

    def ensure_connection(self) -> bool:
        """Убеждается, что соединение активно"""
        if not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except:
            self.connect()
            return self.connection is not None

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает данные пользователя"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            log.error(f"Failed to get user {user_id}: {e}")
            return None

    def save_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Сохраняет данные пользователя"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                # Проверяем, существует ли пользователь
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующего пользователя
                    cursor.execute(
                        """
                        UPDATE users 
                        SET coins = %s, video_bonus = %s, photo_bonus = %s, tryon_bonus = %s,
                            admin_coins = %s, welcome_granted = %s, plan = %s, plan_expiry = %s,
                            updated_at = NOW()
                        WHERE user_id = %s
                        """,
                        (
                            user_data.get("coins", 0),
                            user_data.get("video_bonus", 0),
                            user_data.get("photo_bonus", 0),
                            user_data.get("tryon_bonus", 0),
                            user_data.get("admin_coins", 0),
                            user_data.get("welcome_granted", False),
                            user_data.get("plan", "lite"),
                            user_data.get("plan_expiry"),
                            user_id
                        )
                    )
                else:
                    # Создаем нового пользователя
                    cursor.execute(
                        """
                        INSERT INTO users (user_id, coins, video_bonus, photo_bonus, tryon_bonus,
                                         admin_coins, welcome_granted, plan, plan_expiry, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """,
                        (
                            user_id,
                            user_data.get("coins", 0),
                            user_data.get("video_bonus", 0),
                            user_data.get("photo_bonus", 0),
                            user_data.get("tryon_bonus", 0),
                            user_data.get("admin_coins", 0),
                            user_data.get("welcome_granted", False),
                            user_data.get("plan", "lite"),
                            user_data.get("plan_expiry")
                        )
                    )
                
                self.connection.commit()
                return True
        except Exception as e:
            log.error(f"Failed to save user {user_id}: {e}")
            return False

    def create_user(self, user_id: int, **kwargs) -> bool:
        """Создает нового пользователя"""
        user_data = {
            "coins": 0,
            "video_bonus": 0,
            "photo_bonus": 0,
            "tryon_bonus": 0,
            "admin_coins": 0,
            "welcome_granted": False,
            "plan": "lite",
            "plan_expiry": None,
            **kwargs
        }
        return self.save_user(user_id, user_data)

    # ------------------------------------------------------------------
    # Transaction operations
    # ------------------------------------------------------------------
    
    def atomic_spend_coins(self, user_id: int, cost: int, operation_type: str, status: str = "pending") -> Optional[int]:
        """Атомарно списывает монеты и создает транзакцию"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor() as cursor:
                # Получаем текущий баланс
                cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    log.error(f"User {user_id} not found")
                    return None
                
                current_coins = result[0]
                if current_coins < cost:
                    log.warning(f"Insufficient funds for user {user_id}: {current_coins} < {cost}")
                    return None
                
                # Списываем монеты
                cursor.execute(
                    "UPDATE users SET coins = coins - %s, updated_at = NOW() WHERE user_id = %s",
                    (cost, user_id)
                )
                
                # Создаем транзакцию
                cursor.execute(
                    """
                    INSERT INTO transactions (user_id, what, kind, delta, reason, before, after)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, "coins", "debit", -cost, operation_type, current_coins, current_coins - cost)
                )
                
                transaction_id = cursor.fetchone()[0]
                self.connection.commit()
                
                log.info(f"Spent {cost} coins for user {user_id}, transaction {transaction_id}")
                return transaction_id
                
        except Exception as e:
            log.error(f"Failed to spend coins for user {user_id}: {e}")
            return None

    def update_transaction_status(self, transaction_id: int, status: str) -> bool:
        """Обновляет статус транзакции"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE transactions SET reason = %s WHERE id = %s",
                    (f"{status}_transaction", transaction_id)
                )
                self.connection.commit()
                return True
        except Exception as e:
            log.error(f"Failed to update transaction status: {e}")
            return False

    def add_refund_transaction(self, user_id: int, amount: int, original_transaction_id: Optional[int] = None) -> Optional[int]:
        """Добавляет транзакцию возврата"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor() as cursor:
                # Получаем текущий баланс
                cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                current_coins = result[0]
                
                # Возвращаем монеты
                cursor.execute(
                    "UPDATE users SET coins = coins + %s, updated_at = NOW() WHERE user_id = %s",
                    (amount, user_id)
                )
                
                # Создаем транзакцию возврата
                cursor.execute(
                    """
                    INSERT INTO transactions (user_id, what, kind, delta, reason, before, after)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id, 
                        "coins", 
                        "credit", 
                        amount, 
                        f"refund{'_' + str(original_transaction_id) if original_transaction_id else ''}", 
                        current_coins, 
                        current_coins + amount
                    )
                )
                
                transaction_id = cursor.fetchone()[0]
                self.connection.commit()
                
                log.info(f"Refunded {amount} coins to user {user_id}, transaction {transaction_id}")
                return transaction_id
                
        except Exception as e:
            log.error(f"Failed to add refund transaction: {e}")
            return None

    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает последние транзакции пользователя"""
        if not self.ensure_connection():
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM transactions 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            log.error(f"Failed to get transactions for user {user_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Plan operations
    # ------------------------------------------------------------------
    
    def activate_plan(self, user_id: int, plan: str) -> bool:
        """Активирует план для пользователя"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET plan = %s, updated_at = NOW() WHERE user_id = %s",
                    (plan, user_id)
                )
                self.connection.commit()
                return True
        except Exception as e:
            log.error(f"Failed to activate plan for user {user_id}: {e}")
            return False

    def check_expired_plans(self) -> List[int]:
        """Проверяет истекшие планы"""
        if not self.ensure_connection():
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id FROM users 
                    WHERE plan != 'lite' 
                    AND plan_expiry IS NOT NULL 
                    AND plan_expiry < NOW()
                    """
                )
                results = cursor.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            log.error(f"Failed to check expired plans: {e}")
            return []

    def reset_expired_plan(self, user_id: int) -> bool:
        """Сбрасывает истекший план на lite"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users 
                    SET plan = 'lite', plan_expiry = NULL, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                self.connection.commit()
                return True
        except Exception as e:
            log.error(f"Failed to reset expired plan for user {user_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Job operations
    # ------------------------------------------------------------------
    
    def create_job(self, user_id: int, kind: str, params: Dict[str, Any], cost_charged: int) -> Optional[str]:
        """Создает задачу"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO jobs (user_id, kind, params, cost_charged, status)
                    VALUES (%s, %s, %s, %s, 'queued')
                    RETURNING job_id
                    """,
                    (user_id, kind, json.dumps(params), cost_charged)
                )
                job_id = cursor.fetchone()[0]
                self.connection.commit()
                return str(job_id)
        except Exception as e:
            log.error(f"Failed to create job: {e}")
            return None

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Получает задачу по ID"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
                result = cursor.fetchone()
                if result:
                    result_dict = dict(result)
                    result_dict["params"] = json.loads(result_dict["params"])
                    return result_dict
                return None
        except Exception as e:
            log.error(f"Failed to get job {job_id}: {e}")
            return None

    def update_job_status(self, job_id: str, status: str) -> bool:
        """Обновляет статус задачи"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET status = %s WHERE job_id = %s",
                    (status, job_id)
                )
                self.connection.commit()
                return True
        except Exception as e:
            log.error(f"Failed to update job status: {e}")
            return False

    def use_free_reroll(self, job_id: str) -> bool:
        """Использует бесплатный повтор"""
        if not self.ensure_connection():
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET free_reroll_used = TRUE WHERE job_id = %s AND free_reroll_used = FALSE",
                    (job_id,)
                )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to use free reroll: {e}")
            return False

    # ------------------------------------------------------------------
    # Support operations
    # ------------------------------------------------------------------
    
    def create_support_report(self, user_id: int, text: str, context: Optional[Dict] = None) -> Optional[int]:
        """Создает репорт поддержки"""
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO support_reports (user_id, text, context)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, text, json.dumps(context or {}))
                )
                report_id = cursor.fetchone()[0]
                self.connection.commit()
                return report_id
        except Exception as e:
            log.error(f"Failed to create support report: {e}")
            return None


# Глобальный экземпляр базы данных
db = Database()
