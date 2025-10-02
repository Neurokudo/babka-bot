# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных PostgreSQL
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    log = logging.getLogger("database")
    log.warning("psycopg2 not installed. Database features disabled. Install with: pip install psycopg2-binary")

log = logging.getLogger("database")

# Настройки подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    def __init__(self):
        self.connection = None
        if PSYCOPG2_AVAILABLE:
            self.connect()
            self.init_tables()
        else:
            log.warning("Database features disabled - psycopg2 not available")
    
    def connect(self):
        """Подключение к базе данных"""
        if not PSYCOPG2_AVAILABLE:
            return
            
        try:
            if DATABASE_URL:
                self.connection = psycopg2.connect(DATABASE_URL)
                log.info("Connected to PostgreSQL database")
            else:
                log.warning("DATABASE_URL not set, database features disabled")
                self.connection = None
        except Exception as e:
            log.error(f"Failed to connect to database: {e}")
            self.connection = None
    
    def init_tables(self):
        """Создание таблиц если их нет"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # Таблица пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        coins INTEGER DEFAULT 0,
                        video_bonus INTEGER DEFAULT 2,
                        photo_bonus INTEGER DEFAULT 2,
                        tryon_bonus INTEGER DEFAULT 2,
                        admin_coins INTEGER DEFAULT 0,
                        welcome_granted BOOLEAN DEFAULT FALSE,
                        plan VARCHAR(20) DEFAULT 'lite',
                        plan_expiry TIMESTAMP NULL,
                        videos_left INTEGER DEFAULT 0,
                        photos_left INTEGER DEFAULT 0,
                        videos_allowed INTEGER DEFAULT 0,
                        photos_allowed INTEGER DEFAULT 0,
                        daily_date VARCHAR(10) DEFAULT '',
                        daily_videos INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Таблица транзакций
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        operation_type VARCHAR(20) NOT NULL,
                        coins_spent INTEGER DEFAULT 0,
                        used_bonus BOOLEAN DEFAULT FALSE,
                        bonus_type VARCHAR(20),
                        quality VARCHAR(20),
                        before_value INTEGER,
                        after_value INTEGER,
                        delta INTEGER,
                        reason VARCHAR(50),
                        metadata JSONB,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP,
                        error_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Таблица обработанных платежей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_payments (
                        payment_id VARCHAR(255) PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        amount DECIMAL(10,2),
                        currency VARCHAR(3) DEFAULT 'RUB',
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Таблица платежей (новая система)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        payment_id VARCHAR(255) PRIMARY KEY,
                        idempotency_key VARCHAR(255) UNIQUE,
                        user_id BIGINT NOT NULL,
                        amount DECIMAL(10,2) DEFAULT 0,
                        currency VARCHAR(3) DEFAULT 'RUB',
                        plan VARCHAR(20),
                        metadata JSONB,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Создаем уникальный индекс для идемпотентности
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_idempotency
                    ON payments (idempotency_key)
                """)
                
                # Создаем индексы для быстрого поиска
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_user_id 
                    ON transactions(user_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_created_at 
                    ON transactions(created_at)
                """)
                
                self.connection.commit()
                log.info("Database tables initialized successfully")
                
        except Exception as e:
            log.error(f"Failed to initialize tables: {e}")
            if self.connection:
                self.connection.rollback()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Конвертируем в обычный dict
                    user_data = dict(result)
                    # Добавляем структуру для совместимости с существующим кодом
                    user_data["daily"] = {
                        "date": user_data.get("daily_date", ""),
                        "videos": user_data.get("daily_videos", 0)
                    }
                    user_data["processed_payments"] = set()
                    user_data["jobs"] = {}
                    # Админские монетки отдельно (по умолчанию 0)
                    user_data["admin_coins"] = user_data.get("admin_coins", 0)
                    # Новые поля для системы тарифов
                    user_data["welcome_granted"] = user_data.get("welcome_granted", False)
                    user_data["plan"] = user_data.get("plan", "lite")
                    user_data["plan_expiry"] = user_data.get("plan_expiry")
                    user_data["videos_allowed"] = user_data.get("videos_allowed", 0)
                    user_data["photos_allowed"] = user_data.get("photos_allowed", 0)
                    
                    return user_data
                return None
                
        except Exception as e:
            log.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def save_user(self, user_id: int, user_data: Dict[str, Any]):
        """Сохранить данные пользователя"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # Подготавливаем данные для вставки
                daily_data = user_data.get("daily", {})
                
                cursor.execute("""
                    INSERT INTO users (
                        user_id, coins, video_bonus, photo_bonus, tryon_bonus,
                        admin_coins, welcome_granted, plan, plan_expiry,
                        videos_left, photos_left, videos_allowed, photos_allowed,
                        daily_date, daily_videos, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        coins = EXCLUDED.coins,
                        video_bonus = EXCLUDED.video_bonus,
                        photo_bonus = EXCLUDED.photo_bonus,
                        tryon_bonus = EXCLUDED.tryon_bonus,
                        admin_coins = EXCLUDED.admin_coins,
                        welcome_granted = EXCLUDED.welcome_granted,
                        plan = EXCLUDED.plan,
                        plan_expiry = EXCLUDED.plan_expiry,
                        videos_left = EXCLUDED.videos_left,
                        photos_left = EXCLUDED.photos_left,
                        videos_allowed = EXCLUDED.videos_allowed,
                        photos_allowed = EXCLUDED.photos_allowed,
                        daily_date = EXCLUDED.daily_date,
                        daily_videos = EXCLUDED.daily_videos,
                        updated_at = NOW()
                """, (
                    user_id,
                    user_data.get("coins", 0),
                    user_data.get("video_bonus", 0),
                    user_data.get("photo_bonus", 0),
                    user_data.get("tryon_bonus", 0),
                    user_data.get("admin_coins", 0),
                    user_data.get("welcome_granted", False),
                    user_data.get("plan", "lite"),
                    user_data.get("plan_expiry"),
                    user_data.get("videos_left", 0),
                    user_data.get("photos_left", 0),
                    user_data.get("videos_allowed", 0),
                    user_data.get("photos_allowed", 0),
                    daily_data.get("date", ""),
                    daily_data.get("videos", 0)
                ))
                
                self.connection.commit()
                log.debug(f"User {user_id} saved to database")
                
        except Exception as e:
            log.error(f"Failed to save user {user_id}: {e}")
            if self.connection:
                self.connection.rollback()
    
    def add_transaction(self, user_id: int, operation_type: str, 
                       coins_spent: int = 0, used_bonus: bool = False,
                       bonus_type: str = None, quality: str = "basic",
                       before_value: int = None, after_value: int = None,
                       delta: int = None, reason: str = None,
                       metadata: Dict = None, status: str = "pending") -> Optional[int]:
        """Добавить транзакцию"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transactions (
                        user_id, operation_type, coins_spent, used_bonus,
                        bonus_type, quality, before_value, after_value,
                        delta, reason, metadata, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (user_id, operation_type, coins_spent, used_bonus, 
                     bonus_type, quality, before_value, after_value,
                     delta, reason, json.dumps(metadata) if metadata else None, status))
                
                transaction_id = cursor.fetchone()[0]
                self.connection.commit()
                
                log.debug(f"Transaction {transaction_id} added for user {user_id}")
                return transaction_id
                
        except Exception as e:
            log.error(f"Failed to add transaction for user {user_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def update_transaction_status(self, transaction_id: int, status: str):
        """Обновить статус транзакции"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                if status == "completed":
                    cursor.execute("""
                        UPDATE transactions 
                        SET status = %s, completed_at = NOW()
                        WHERE id = %s
                    """, (status, transaction_id))
                elif status == "error":
                    cursor.execute("""
                        UPDATE transactions 
                        SET status = %s, error_at = NOW()
                        WHERE id = %s
                    """, (status, transaction_id))
                else:
                    cursor.execute("""
                        UPDATE transactions 
                        SET status = %s
                        WHERE id = %s
                    """, (status, transaction_id))
                
                self.connection.commit()
                
        except Exception as e:
            log.error(f"Failed to update transaction {transaction_id}: {e}")
            if self.connection:
                self.connection.rollback()
    
    def is_payment_processed(self, payment_id: str) -> bool:
        """Проверить, был ли платеж уже обработан"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM processed_payments WHERE payment_id = %s",
                    (payment_id,)
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            log.error(f"Failed to check payment {payment_id}: {e}")
            return False
    
    def mark_payment_processed(self, payment_id: str, user_id: int, 
                             amount: float, currency: str, metadata: Dict):
        """Отметить платеж как обработанный"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO processed_payments (
                        payment_id, user_id, amount, currency, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s
                    )
                """, (payment_id, user_id, amount, currency, json.dumps(metadata)))
                
                self.connection.commit()
                
        except Exception as e:
            log.error(f"Failed to mark payment {payment_id} as processed: {e}")
            if self.connection:
                self.connection.rollback()
    
    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить историю транзакций пользователя"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM transactions 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            log.error(f"Failed to get transactions for user {user_id}: {e}")
            return []
    
    def create_payment(self, payment_id: str, idempotency_key: str, user_id: int,
                       amount: float, currency: str = "RUB", plan: str = None,
                       metadata: Dict = None) -> bool:
        """Создать запись о платеже"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO payments (
                        payment_id, idempotency_key, user_id, amount, currency, plan, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """, (payment_id, idempotency_key, user_id, amount, currency, plan,
                     json.dumps(metadata) if metadata else None))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to create payment {payment_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Обновить статус платежа"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE payments 
                    SET status = %s
                    WHERE payment_id = %s
                """, (status, payment_id))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to update payment {payment_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о платеже"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM payments WHERE payment_id = %s",
                    (payment_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            log.error(f"Failed to get payment {payment_id}: {e}")
            return None
    
    def is_payment_exists(self, payment_id: str) -> bool:
        """Проверить существование платежа"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM payments WHERE payment_id = %s",
                    (payment_id,)
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            log.error(f"Failed to check payment {payment_id}: {e}")
            return False
    
    def activate_plan(self, user_id: int, plan: str) -> bool:
        """Активировать тариф для пользователя"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                # Обновляем план и дату окончания (30 дней)
                cursor.execute("""
                    UPDATE users 
                    SET plan = %s, plan_expiry = NOW() + INTERVAL '30 days'
                    WHERE user_id = %s
                """, (plan, user_id))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to activate plan {plan} for user {user_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def grant_welcome_bonus(self, user_id: int) -> bool:
        """Выдать приветственный бонус новому пользователю"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                # Проверяем, не получал ли уже пользователь приветственный бонус
                cursor.execute("""
                    SELECT welcome_granted FROM users WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    return False  # Уже получал
                
                # Выдаем бонусы 2/2/2
                cursor.execute("""
                    UPDATE users 
                    SET video_bonus = 2, photo_bonus = 2, tryon_bonus = 2,
                        welcome_granted = TRUE
                    WHERE user_id = %s
                """, (user_id,))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to grant welcome bonus for user {user_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def check_expired_plans(self) -> List[int]:
        """Проверить истекшие тарифы"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id FROM users 
                    WHERE plan_expiry IS NOT NULL 
                    AND plan_expiry < NOW() 
                    AND plan != 'lite'
                """)
                
                results = cursor.fetchall()
                return [row[0] for row in results]
                
        except Exception as e:
            log.error(f"Failed to check expired plans: {e}")
            return []
    
    def reset_expired_plan(self, user_id: int) -> bool:
        """Сбросить истекший тариф на lite"""
        if not PSYCOPG2_AVAILABLE or not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET plan = 'lite', plan_expiry = NULL,
                        videos_allowed = 0, photos_allowed = 0
                    WHERE user_id = %s
                """, (user_id,))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to reset expired plan for user {user_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def close(self):
        """Закрыть соединение с базой данных"""
        if PSYCOPG2_AVAILABLE and self.connection:
            self.connection.close()
            log.info("Database connection closed")

# Глобальный экземпляр базы данных
db = Database()
