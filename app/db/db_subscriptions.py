"""
Модуль для работы с подписками, пользователями и транзакциями
"""

import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

log = logging.getLogger("db_subscriptions")

# Подключение к базе данных
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

def init_tables():
    """Инициализация таблиц базы данных"""
    with db_conn() as conn:
        # Создаем таблицу пользователей
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                plan TEXT DEFAULT 'lite',
                plan_expiry TIMESTAMP,
                coins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем таблицу подписок
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT NOT NULL,
                plan TEXT NOT NULL,
                coins INTEGER DEFAULT 0,
                price_rub INTEGER NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                payment_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем таблицу транзакций
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT,
                feature TEXT,
                coins_spent INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )
        """)
        
        conn.commit()
        log.info("Database tables initialized")

def create_subscription(user_id: int, plan: str, coins: int, price_rub: int,
                       duration_days: int = 30, payment_id: str | None = None):
    """
    Добавляет новую подписку и обновляет профиль пользователя.
    """
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                # PostgreSQL синтаксис
                conn.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, payment_id)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '%s days')
                """, (user_id, plan, coins, price_rub, duration_days))
                
                conn.execute("""
                    UPDATE users
                    SET plan = %s, plan_expiry = CURRENT_TIMESTAMP + INTERVAL '%s days', coins = coins + %s
                    WHERE user_id = %s
                """, (plan, duration_days, coins, user_id))
            else:
                # SQLite синтаксис
                conn.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, payment_id)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, datetime('now', ?))
                """, (user_id, plan, coins, price_rub, f'+{duration_days} days'))
                
                conn.execute("""
                    UPDATE users
                    SET plan = ?, plan_expiry = datetime('now', ?), coins = coins + ?
                    WHERE user_id = ?
                """, (plan, f'+{duration_days} days', coins, user_id))
            
            conn.commit()
            log.info(f"Subscription created for user {user_id}: {plan} plan, {coins} coins")
            
    except Exception as e:
        log.error(f"Failed to create subscription for user {user_id}: {e}")
        raise

def charge_feature(user_id: int, feature: str, cost: int, note: str | None = None) -> bool:
    """
    Списывает монеты за использование функции.
    Возвращает True, если хватает баланса.
    """
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Проверяем баланс пользователя
            if is_postgres:
                bal = conn.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,)).fetchone()
            else:
                bal = conn.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)).fetchone()
                
            if not bal or bal[0] < cost:
                log.warning(f"Insufficient balance for user {user_id}: {bal[0] if bal else 0} < {cost}")
                return False
            
            # Списываем монеты
            if is_postgres:
                conn.execute("UPDATE users SET coins = coins - %s WHERE user_id = %s", (cost, user_id))
                conn.execute("""
                    INSERT INTO transactions (user_id, feature, coins_spent, note)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, feature, cost, note))
            else:
                conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
                conn.execute("""
                    INSERT INTO transactions (user_id, feature, coins_spent, note)
                    VALUES (?, ?, ?, ?)
                """, (user_id, feature, cost, note))
            
            conn.commit()
            log.info(f"Charged {cost} coins from user {user_id} for feature {feature}")
            return True
            
    except Exception as e:
        log.error(f"Failed to charge feature for user {user_id}: {e}")
        return False

def check_expired_subscriptions():
    """
    Проверяет и деактивирует истёкшие подписки.
    """
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Находим просроченные подписки
            if is_postgres:
                expired = conn.execute("""
                    SELECT user_id FROM subscriptions
                    WHERE is_active = TRUE AND end_date < CURRENT_TIMESTAMP
                """).fetchall()
            else:
                expired = conn.execute("""
                    SELECT user_id FROM subscriptions
                    WHERE is_active = 1 AND end_date < CURRENT_TIMESTAMP
                """).fetchall()
            
            for (uid,) in expired:
                # Сбрасываем план пользователя на lite
                if is_postgres:
                    conn.execute("UPDATE users SET plan='lite', plan_expiry=NULL WHERE user_id=%s", (uid,))
                    conn.execute("UPDATE subscriptions SET is_active=FALSE WHERE user_id=%s", (uid,))
                else:
                    conn.execute("UPDATE users SET plan='lite', plan_expiry=NULL WHERE user_id=?", (uid,))
                    conn.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=?", (uid,))
                log.info(f"Expired subscription deactivated for user {uid}")
            
            conn.commit()
            if expired:
                log.info(f"Processed {len(expired)} expired subscriptions")
                
    except Exception as e:
        log.error(f"Failed to check expired subscriptions: {e}")

def get_user_balance(user_id: int) -> int:
    """Получить баланс пользователя"""
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                result = conn.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,)).fetchone()
            else:
                result = conn.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return result[0] if result else 0
    except Exception as e:
        log.error(f"Failed to get balance for user {user_id}: {e}")
        return 0

def get_user_plan(user_id: int) -> Dict[str, Any]:
    """Получить информацию о плане пользователя"""
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                result = conn.execute("""
                    SELECT plan, plan_expiry, coins FROM users WHERE user_id = %s
                """, (user_id,)).fetchone()
            else:
                result = conn.execute("""
                    SELECT plan, plan_expiry, coins FROM users WHERE user_id = ?
                """, (user_id,)).fetchone()
            
            if result:
                plan, expiry, coins = result
                return {
                    "plan": plan,
                    "expiry": expiry,
                    "coins": coins,
                    "is_active": expiry is None or expiry > datetime.now()
                }
            return {"plan": "lite", "expiry": None, "coins": 0, "is_active": False}
            
    except Exception as e:
        log.error(f"Failed to get plan for user {user_id}: {e}")
        return {"plan": "lite", "expiry": None, "coins": 0, "is_active": False}

def create_or_update_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Создать или обновить пользователя"""
    try:
        with db_conn() as conn:
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Проверяем, существует ли пользователь
            if is_postgres:
                existing = conn.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,)).fetchone()
            else:
                existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
            
            if existing:
                # Обновляем существующего пользователя
                if is_postgres:
                    conn.execute("""
                        UPDATE users SET username = %s, first_name = %s, last_name = %s
                        WHERE user_id = %s
                    """, (username, first_name, last_name, user_id))
                else:
                    conn.execute("""
                        UPDATE users SET username = ?, first_name = ?, last_name = ?
                        WHERE user_id = ?
                    """, (username, first_name, last_name, user_id))
            else:
                # Создаем нового пользователя
                if is_postgres:
                    conn.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, coins)
                        VALUES (%s, %s, %s, %s, 0)
                    """, (user_id, username, first_name, last_name))
                else:
                    conn.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, coins)
                        VALUES (?, ?, ?, ?, 0)
                    """, (user_id, username, first_name, last_name))
            
            conn.commit()
            log.info(f"User {user_id} created/updated")
            
    except Exception as e:
        log.error(f"Failed to create/update user {user_id}: {e}")

# Инициализируем таблицы при импорте модуля
try:
    init_tables()
except Exception as e:
    log.warning(f"Failed to initialize database tables: {e}")
