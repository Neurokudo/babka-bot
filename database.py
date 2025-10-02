# -*- coding: utf-8 -*-
"""Работа с PostgreSQL для Babka Bot (монетная модель)."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:  # pragma: no cover
    PSYCOPG2_AVAILABLE = False
    logging.getLogger("database").warning(
        "psycopg2 not installed. Database features disabled. Install with: pip install psycopg2-binary"
    )

log = logging.getLogger("database")
DATABASE_URL = os.getenv("DATABASE_URL")


class Database:
    def __init__(self) -> None:
        self.connection = None
        if PSYCOPG2_AVAILABLE:
            self.connect()
            self.init_tables()

    # ------------------------------------------------------------------
    # Low level helpers
    # ------------------------------------------------------------------
    def connect(self) -> None:
        if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
            log.warning("DATABASE_URL not set, database features disabled")
            return
        try:
            self.connection = psycopg2.connect(DATABASE_URL)
            log.info("Connected to PostgreSQL database")
        except Exception as exc:  # pragma: no cover
            log.error("Failed to connect to database: %s", exc)
            self.connection = None

    def init_tables(self) -> None:
        if not self.connection:
            return
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        coins INTEGER NOT NULL DEFAULT 0,
                        plan VARCHAR(20) NOT NULL DEFAULT 'lite',
                        plan_expiry TIMESTAMP NULL,
                        admin_coins INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(user_id),
                        operation_type VARCHAR(50) NOT NULL,
                        coins_spent INTEGER NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(user_id),
                        subscription_type VARCHAR(50),
                        amount DECIMAL(10,2) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        idempotent_key VARCHAR(255) UNIQUE
                    )
                    """
                )

                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)"
                )
            self.connection.commit()
            log.info("Database tables initialized successfully")
        except Exception as exc:  # pragma: no cover
            log.error("Failed to initialize tables: %s", exc)
            if self.connection:
                self.connection.rollback()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        if not self.connection:
            return None
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                user = dict(result)
                user.setdefault("coins", 0)
                user.setdefault("admin_coins", 0)
                user.setdefault("plan", "lite")
                user.setdefault("plan_expiry", None)
                user.setdefault("created_at", datetime.utcnow())
                user.setdefault("updated_at", datetime.utcnow())
                user.setdefault("jobs", {})
                user.setdefault("last_job", None)
                return user
        except Exception as exc:  # pragma: no cover
            log.error("Failed to get user %s: %s", user_id, exc)
            return None

    def save_user(self, user_id: int, data: Dict[str, Any]) -> None:
        if not self.connection:
            return
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (user_id, coins, plan, plan_expiry, admin_coins, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        coins = EXCLUDED.coins,
                        plan = EXCLUDED.plan,
                        plan_expiry = EXCLUDED.plan_expiry,
                        admin_coins = EXCLUDED.admin_coins,
                        updated_at = NOW()
                    """,
                    (
                        user_id,
                        data.get("coins", 0),
                        data.get("plan", "lite"),
                        data.get("plan_expiry"),
                        data.get("admin_coins", 0),
                    ),
                )
            self.connection.commit()
        except Exception as exc:  # pragma: no cover
            log.error("Failed to save user %s: %s", user_id, exc)
            self.connection.rollback()

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    def add_transaction(
        self,
        user_id: int,
        operation_type: str,
        coins_spent: int,
        status: str = "pending",
    ) -> Optional[int]:
        if not self.connection:
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, operation_type, coins_spent, status),
                )
                tx_id = cursor.fetchone()[0]
            self.connection.commit()
            return tx_id
        except Exception as exc:  # pragma: no cover
            log.error("Failed to add transaction for user %s: %s", user_id, exc)
            self.connection.rollback()
            return None

    def update_transaction_status(self, transaction_id: int, status: str) -> None:
        if not self.connection:
            return
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE transactions SET status = %s WHERE id = %s",
                    (status, transaction_id),
                )
            self.connection.commit()
        except Exception as exc:  # pragma: no cover
            log.error("Failed to update transaction %s: %s", transaction_id, exc)
            self.connection.rollback()

    def atomic_spend_coins(
        self,
        user_id: int,
        cost: int,
        operation_type: str,
        status: str = "pending",
    ) -> Optional[int]:
        if not self.connection:
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET coins = coins - %s, updated_at = NOW()
                    WHERE user_id = %s AND coins >= %s
                    RETURNING coins
                    """,
                    (cost, user_id, cost),
                )
                result = cursor.fetchone()
                if not result:
                    return None
                cursor.execute(
                    """
                    INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, operation_type, cost, status),
                )
                tx_id = cursor.fetchone()[0]
            self.connection.commit()
            return tx_id
        except Exception as exc:  # pragma: no cover
            log.error("Error in atomic_spend_coins for user %s: %s", user_id, exc)
            self.connection.rollback()
            return None

    def add_refund_transaction(
        self,
        user_id: int,
        amount: int,
        original_transaction_id: Optional[int] = None,
    ) -> Optional[int]:
        if not self.connection:
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, "refund", -amount, "completed"),
                )
                tx_id = cursor.fetchone()[0]
            self.connection.commit()
            return tx_id
        except Exception as exc:  # pragma: no cover
            log.error("Failed to log refund for user %s: %s", user_id, exc)
            self.connection.rollback()
            return None

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    def create_payment(
        self,
        payment_id: str,
        user_id: int,
        subscription_type: Optional[str],
        amount: float,
        status: str = "pending",
        idempotent_key: Optional[str] = None,
    ) -> bool:
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO payments (id, user_id, subscription_type, amount, status, idempotent_key)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (payment_id, user_id, subscription_type, amount, status, idempotent_key),
                )
            self.connection.commit()
            return True
        except Exception as exc:  # pragma: no cover
            log.error("Failed to create payment %s: %s", payment_id, exc)
            self.connection.rollback()
            return False

    def update_payment_status(self, payment_id: str, status: str) -> bool:
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE payments SET status = %s WHERE id = %s", (status, payment_id))
            self.connection.commit()
            return True
        except Exception as exc:  # pragma: no cover
            log.error("Failed to update payment %s: %s", payment_id, exc)
            self.connection.rollback()
            return False

    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        if not self.connection:
            return None
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as exc:  # pragma: no cover
            log.error("Failed to get payment %s: %s", payment_id, exc)
            return None

    # ------------------------------------------------------------------
    # Business helpers
    # ------------------------------------------------------------------
    def activate_plan(self, user_id: int, plan: str) -> bool:
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET plan = %s,
                        plan_expiry = NOW() + INTERVAL '30 days',
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (plan, user_id),
                )
            self.connection.commit()
            return True
        except Exception as exc:  # pragma: no cover
            log.error("Failed to activate plan %s for user %s: %s", plan, user_id, exc)
            self.connection.rollback()
            return False

    def check_expired_plans(self) -> List[int]:
        if not self.connection:
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
                return [row[0] for row in cursor.fetchall()]
        except Exception as exc:  # pragma: no cover
            log.error("Failed to check expired plans: %s", exc)
            return []

    def reset_expired_plan(self, user_id: int) -> bool:
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET plan = 'lite', plan_expiry = NULL, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
            self.connection.commit()
            return True
        except Exception as exc:  # pragma: no cover
            log.error("Failed to reset expired plan for user %s: %s", user_id, exc)
            self.connection.rollback()
            return False


# Глобальный экземпляр
_db_instance: Optional[Database] = None


def _get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def reset_connection_for_tests():  # pragma: no cover - используется в тестах
    global _db_instance
    _db_instance = Database()


db = _get_db()
