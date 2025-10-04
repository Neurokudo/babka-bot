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
        cur = conn.cursor()
        
        # Определяем тип базы данных
        database_url = os.getenv("DATABASE_URL", "")
        is_postgres = database_url.startswith("postgresql://")
        
        if is_postgres:
            # PostgreSQL синтаксис для Railway
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    plan TEXT DEFAULT NULL,
                    plan_expiry TIMESTAMP,
                    coins INTEGER DEFAULT 0,
                    auto_renew BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем колонку auto_renew если её нет (миграция)
            try:
                # Проверяем, существует ли колонка
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'auto_renew'
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE users ADD COLUMN auto_renew BOOLEAN DEFAULT TRUE")
                    log.info("Added auto_renew column to users table")
                else:
                    log.debug("auto_renew column already exists")
            except Exception as e:
                # Колонка уже существует или другая ошибка
                log.debug(f"auto_renew column check failed: {e}")
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
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
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    feature TEXT,
                    coins_spent INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    note TEXT
                )
            """)
        else:
            # SQLite синтаксис для локальной разработки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    plan TEXT DEFAULT NULL,
                    plan_expiry TIMESTAMP,
                    coins INTEGER DEFAULT 0,
                    auto_renew BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем колонку auto_renew если её нет (миграция)
            try:
                # Проверяем, существует ли колонка в SQLite
                cur.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cur.fetchall()]
                if 'auto_renew' not in columns:
                    cur.execute("ALTER TABLE users ADD COLUMN auto_renew BOOLEAN DEFAULT 1")
                    log.info("Added auto_renew column to users table")
                else:
                    log.debug("auto_renew column already exists")
            except Exception as e:
                # Колонка уже существует или другая ошибка
                log.debug(f"auto_renew column check failed: {e}")
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    plan TEXT NOT NULL,
                    coins INTEGER DEFAULT 0,
                    price_rub INTEGER NOT NULL,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
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
        log.info("Database tables initialized successfully")

def create_subscription(user_id: int, plan: str, coins: int, price_rub: int,
                       duration_days: int = 30, payment_id: str | None = None):
    """
    Добавляет новую подписку и обновляет профиль пользователя.
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                # Деактивируем предыдущие подписки
                cur.execute("UPDATE subscriptions SET is_active = FALSE WHERE user_id = %s", (user_id,))
                
                # PostgreSQL синтаксис
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, payment_id)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + (%s || ' days')::interval, %s)
                """, (user_id, plan, coins, price_rub, duration_days, payment_id))
                
                cur.execute("""
                    UPDATE users
                    SET plan = %s, plan_expiry = CURRENT_TIMESTAMP + (%s || ' days')::interval, coins = coins + %s
                    WHERE user_id = %s
                """, (plan, duration_days, coins, user_id))
            else:
                # Деактивируем предыдущие подписки
                cur.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
                
                # SQLite синтаксис
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, coins, price_rub, start_date, end_date, payment_id)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, datetime('now', '+? days'), ?)
                """, (user_id, plan, coins, price_rub, duration_days, payment_id))
                
                cur.execute("""
                    UPDATE users
                    SET plan = ?, plan_expiry = datetime('now', '+? days'), coins = coins + ?
                    WHERE user_id = ?
                """, (plan, duration_days, coins, user_id))
            
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
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Проверяем баланс пользователя
            if is_postgres:
                cur.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
                bal = cur.fetchone()
            else:
                cur.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
                bal = cur.fetchone()
                
            if not bal or bal[0] < cost:
                log.warning(f"Insufficient balance for user {user_id}: {bal[0] if bal else 0} < {cost}")
                return False
            
            # Списываем монеты
            if is_postgres:
                cur.execute("UPDATE users SET coins = coins - %s WHERE user_id = %s", (cost, user_id))
                cur.execute("""
                    INSERT INTO transactions (user_id, feature, coins_spent, note)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, feature, cost, note))
            else:
                cur.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
                cur.execute("""
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
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Находим просроченные подписки
            if is_postgres:
                cur.execute("""
                    SELECT user_id FROM subscriptions
                    WHERE is_active = TRUE AND end_date < CURRENT_TIMESTAMP
                """)
                expired = cur.fetchall()
            else:
                cur.execute("""
                    SELECT user_id FROM subscriptions
                    WHERE is_active = 1 AND end_date < CURRENT_TIMESTAMP
                """)
                expired = cur.fetchall()
            
            for (uid,) in expired:
                # Сбрасываем план пользователя на lite, обнуляем монеты и plan_expiry
                if is_postgres:
                    cur.execute("UPDATE users SET plan='lite', plan_expiry=NULL, coins=0 WHERE user_id=%s", (uid,))
                    cur.execute("UPDATE subscriptions SET is_active=FALSE WHERE user_id=%s", (uid,))
                else:
                    cur.execute("UPDATE users SET plan='lite', plan_expiry=NULL, coins=0 WHERE user_id=?", (uid,))
                    cur.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=?", (uid,))
                log.info(f"Expired subscription deactivated for user {uid}")
            
            conn.commit()
            if expired:
                log.info(f"Processed {len(expired)} expired subscriptions")
                
    except Exception as e:
        log.error(f"Failed to check expired subscriptions: {e}")

def get_active_subscribers():
    """
    Получить список всех активных подписчиков
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("SELECT * FROM subscriptions WHERE is_active=TRUE")
                return cur.fetchall()
            else:
                cur.execute("SELECT * FROM subscriptions WHERE is_active=1")
                return cur.fetchall()
                
    except Exception as e:
        log.error(f"Failed to get active subscribers: {e}")
        return []

def get_user_balance(user_id: int) -> int:
    """Получить баланс пользователя"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
            else:
                cur.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
                result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        log.error(f"Failed to get balance for user {user_id}: {e}")
        return 0

def get_user_plan(user_id: int) -> Dict[str, Any]:
    """Получить информацию о плане пользователя"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("""
                    SELECT plan, plan_expiry, coins, auto_renew FROM users WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
            else:
                cur.execute("""
                    SELECT plan, plan_expiry, coins, auto_renew FROM users WHERE user_id = ?
                """, (user_id,))
                result = cur.fetchone()
            
            if result:
                plan, expiry, coins, auto_renew = result
                is_active = False
                
                # Если есть план (не None и не пустой), считаем подписку активной
                if plan and plan.strip():
                    is_active = True
                    
                    # Если есть expiry, проверяем срок действия
                    if expiry is not None:
                        try:
                            # Пытаемся преобразовать expiry в datetime если это строка
                            if isinstance(expiry, str):
                                from datetime import datetime
                                expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                                is_active = expiry_dt > datetime.now()
                            else:
                                is_active = expiry > datetime.now()
                        except:
                            # При ошибке парсинга expiry, считаем подписку активной если есть план
                            is_active = True
                
                # Логируем результат для отладки
                print(f"[DB] get_user_plan user_id={user_id} plan={plan} expiry={expiry} coins={coins} is_active={is_active}")
                
                return {
                    "plan": plan,
                    "expiry": expiry,
                    "coins": coins,
                    "is_active": is_active,
                    "auto_renew": auto_renew
                }
            return {"plan": None, "expiry": None, "coins": 0, "is_active": False, "auto_renew": True}
            
    except Exception as e:
        log.error(f"Failed to get plan for user {user_id}: {e}")
        return {"plan": "lite", "expiry": None, "coins": 0, "is_active": False}

def cancel_subscription(user_id: int) -> bool:
    """Отменить автопродление подписки"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("UPDATE users SET auto_renew = FALSE WHERE user_id = %s", (user_id,))
            else:
                cur.execute("UPDATE users SET auto_renew = 0 WHERE user_id = ?", (user_id,))
            
            conn.commit()
            log.info(f"Subscription auto-renewal cancelled for user {user_id}")
            return True
            
    except Exception as e:
        log.error(f"Failed to cancel subscription for user {user_id}: {e}")
        return False

def create_or_update_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Создать или обновить пользователя"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Проверяем, существует ли пользователь
            if is_postgres:
                cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                existing = cur.fetchone()
            else:
                cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                existing = cur.fetchone()
            
            if existing:
                # Обновляем существующего пользователя
                if is_postgres:
                    cur.execute("""
                        UPDATE users SET username = %s, first_name = %s, last_name = %s
                        WHERE user_id = %s
                    """, (username, first_name, last_name, user_id))
                else:
                    cur.execute("""
                        UPDATE users SET username = ?, first_name = ?, last_name = ?
                        WHERE user_id = ?
                    """, (username, first_name, last_name, user_id))
            else:
                # Создаем нового пользователя
                if is_postgres:
                    cur.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, coins)
                        VALUES (%s, %s, %s, %s, 0)
                    """, (user_id, username, first_name, last_name))
                else:
                    cur.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, coins)
                        VALUES (?, ?, ?, ?, 0)
                    """, (user_id, username, first_name, last_name))
            
            conn.commit()
            log.info(f"User {user_id} created/updated")
            
    except Exception as e:
        log.error(f"Failed to create/update user {user_id}: {e}")

def update_user_balance(user_id: int, coins_delta: int, note: str = None) -> bool:
    """
    Обновить баланс пользователя (добавить или отнять монеты)
    
    Args:
        user_id: ID пользователя
        coins_delta: Изменение баланса (положительное для пополнения, отрицательное для списания)
        note: Примечание к операции
    
    Returns:
        bool: True если операция успешна
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Проверяем текущий баланс
            if is_postgres:
                cur.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
            else:
                cur.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
                result = cur.fetchone()
            
            if not result:
                log.warning(f"User {user_id} not found")
                return False
            
            current_balance = result[0]
            new_balance = current_balance + coins_delta
            
            if new_balance < 0:
                log.warning(f"Insufficient balance for user {user_id}: {current_balance} + {coins_delta} = {new_balance}")
                return False
            
            # Обновляем баланс
            if is_postgres:
                cur.execute("UPDATE users SET coins = %s WHERE user_id = %s", (new_balance, user_id))
            else:
                cur.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_balance, user_id))
            
            # Записываем транзакцию
            if is_postgres:
                cur.execute("""
                    INSERT INTO transactions (user_id, feature, coins_spent, note)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, "balance_update", abs(coins_delta), note or f"Balance update: {coins_delta:+d}"))
            else:
                cur.execute("""
                    INSERT INTO transactions (user_id, feature, coins_spent, note)
                    VALUES (?, ?, ?, ?)
                """, (user_id, "balance_update", abs(coins_delta), note or f"Balance update: {coins_delta:+d}"))
            
            conn.commit()
            log.info(f"Balance updated for user {user_id}: {current_balance} -> {new_balance} ({coins_delta:+d})")
            return True
            
    except Exception as e:
        log.error(f"Failed to update balance for user {user_id}: {e}")
        return False

def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить информацию о платеже по ID
    
    Args:
        payment_id: ID платежа в YooKassa
    
    Returns:
        Dict с информацией о подписке или None если не найдена
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("""
                    SELECT * FROM subscriptions WHERE payment_id = %s
                """, (payment_id,))
                result = cur.fetchone()
            else:
                cur.execute("""
                    SELECT * FROM subscriptions WHERE payment_id = ?
                """, (payment_id,))
                result = cur.fetchone()
            
            if result:
                columns = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else None
                if columns:
                    return dict(zip(columns, result))
                else:
                    # Для SQLite возвращаем как есть
                    return {
                        "id": result[0],
                        "user_id": result[1],
                        "plan": result[2],
                        "coins": result[3],
                        "price_rub": result[4],
                        "start_date": result[5],
                        "end_date": result[6],
                        "is_active": result[7],
                        "payment_id": result[8],
                        "created_at": result[9]
                    }
            return None
            
    except Exception as e:
        log.error(f"Failed to get payment by ID {payment_id}: {e}")
        return None

def get_user_subscription_history(user_id: int) -> List[Dict[str, Any]]:
    """
    Получить историю подписок пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        List[Dict] с историей подписок
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("""
                    SELECT * FROM subscriptions WHERE user_id = %s ORDER BY created_at DESC
                """, (user_id,))
                results = cur.fetchall()
            else:
                cur.execute("""
                    SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC
                """, (user_id,))
                results = cur.fetchall()
            
            subscriptions = []
            for result in results:
                subscriptions.append({
                    "id": result[0],
                    "user_id": result[1],
                    "plan": result[2],
                    "coins": result[3],
                    "price_rub": result[4],
                    "start_date": result[5],
                    "end_date": result[6],
                    "is_active": result[7],
                    "payment_id": result[8],
                    "created_at": result[9]
                })
            
            return subscriptions
            
    except Exception as e:
        log.error(f"Failed to get subscription history for user {user_id}: {e}")
        return []

def get_user_transaction_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Получить историю транзакций пользователя
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество записей
    
    Returns:
        List[Dict] с историей транзакций
    """
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            if is_postgres:
                cur.execute("""
                    SELECT * FROM transactions WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s
                """, (user_id, limit))
                results = cur.fetchall()
            else:
                cur.execute("""
                    SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
                """, (user_id, limit))
                results = cur.fetchall()
            
            transactions = []
            for result in results:
                transactions.append({
                    "id": result[0],
                    "user_id": result[1],
                    "feature": result[2],
                    "coins_spent": result[3],
                    "timestamp": result[4],
                    "note": result[5]
                })
            
            return transactions
            
    except Exception as e:
        log.error(f"Failed to get transaction history for user {user_id}: {e}")
        return []

def activate_user_plan(user_id: int, plan_name: str, coins: int) -> bool:
    """Активировать план для пользователя"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Вычисляем дату окончания подписки (30 дней)
            from datetime import datetime, timedelta
            expiry_date = datetime.now() + timedelta(days=30)
            
            # Проверяем, существует ли пользователь
            if is_postgres:
                cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                existing = cur.fetchone()
            else:
                cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                existing = cur.fetchone()
            
            if existing:
                # Обновляем существующего пользователя
                if is_postgres:
                    cur.execute("""
                        UPDATE users SET plan = %s, plan_expiry = %s, coins = coins + %s
                        WHERE user_id = %s
                    """, (plan_name, expiry_date, coins, user_id))
                else:
                    cur.execute("""
                        UPDATE users SET plan = ?, plan_expiry = ?, coins = coins + ?
                        WHERE user_id = ?
                    """, (plan_name, expiry_date, coins, user_id))
            else:
                # Создаем нового пользователя
                if is_postgres:
                    cur.execute("""
                        INSERT INTO users (user_id, plan, plan_expiry, coins)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, plan_name, expiry_date, coins))
                else:
                    cur.execute("""
                        INSERT INTO users (user_id, plan, plan_expiry, coins)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, plan_name, expiry_date, coins))
            
            conn.commit()
            log.info(f"Activated plan {plan_name} for user {user_id} with {coins} coins")
            return True
            
    except Exception as e:
        log.error(f"Failed to activate plan {plan_name} for user {user_id}: {e}")
        return False

# Инициализируем таблицы при импорте модуля
try:
    init_tables()
except Exception as e:
    log.warning(f"Failed to initialize database tables: {e}")