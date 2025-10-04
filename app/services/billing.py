"""
BillingService - сервис для управления биллингом и транзакциями
Заменяет старый app.billing модуль
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from app.services.pricing import feature_cost_coins

log = logging.getLogger("billing")

# Глобальное хранилище состояний пользователей (временное решение)
user_states = {}

# Глобальное хранилище задач
user_jobs = {}

def get_user_state(user_id: int) -> Dict[str, Any]:
    """Получить состояние пользователя"""
    if user_id not in user_states:
        # Пытаемся получить баланс из БД, если доступна
        try:
            from app.db.queries import db_manager
            user = db_manager.get_user(user_id)
            initial_coins = user.balance if user else 100
        except Exception:
            initial_coins = 100  # Заглушка при недоступности БД
            
        user_states[user_id] = {
            "coins": initial_coins,
            "current_job_id": None,
            "jobs": {},
            "tariff": None,
            "tariff_expires": None
        }
    return user_states[user_id]

def can_spend(user_id: int, feature_key: str) -> bool:
    """Проверить, может ли пользователь потратить монеты на функцию"""
    try:
        # Получаем данные о подписке и балансе
        subscription_data = check_subscription(user_id)
        current_balance = subscription_data.get("coins", 0)
        cost = feature_cost_coins(feature_key)
        
        # Проверяем только баланс монеток - монетки сохраняются даже при истечении подписки
        # Пользователь может тратить монетки, пока они есть на счету
        
        # Логируем проверку
        log.info(f"[CanSpend] user_id={user_id} balance={current_balance} cost={cost} feature={feature_key} active={subscription_data.get('is_active')} source=db")
        
        return current_balance >= cost
    except Exception as e:
        log.warning(f"Failed to check spending ability for user {user_id}: {e}")
        return False

def hold_and_start(user_id: int, feature_type: str, quality: str = "basic") -> str:
    """Заблокировать монеты и начать задачу"""
    try:
        # Получаем актуальный баланс из базы данных
        from app.services.billing import check_subscription
        subscription_data = check_subscription(user_id)
        current_balance = subscription_data.get("coins", 0)
        
        # Определяем стоимость в зависимости от типа функции
        if feature_type == "video":
            cost = 20 if quality == "audio" else 16
        elif feature_type == "transform":
            cost = 1
        elif feature_type == "tryon":
            cost = 3
        elif feature_type == "json":
            cost = 20
        else:
            cost = 1
        
        # Проверяем, хватает ли монет
        if current_balance < cost:
            raise ValueError(f"Недостаточно монет. Нужно: {cost}, у вас: {current_balance}")
        
        # Логируем начало задачи
        log.info(f"[HoldAndStart] user_id={user_id} balance={current_balance} cost={cost} feature={feature_type} source=db")
        
    except Exception as e:
        log.error(f"Failed to start task for user {user_id}: {e}")
        raise
    
    # Создаем задачу
    job_id = f"{user_id}_{feature_type}_{int(datetime.now().timestamp())}"
    
    job_data = {
        "user_id": user_id,
        "feature_type": feature_type,
        "quality": quality,
        "coin_cost": cost,
        "status": "processing",
        "created_at": datetime.now(),
        "retry_count": 0
    }
    
    # Сохраняем задачу
    user_jobs[job_id] = job_data
    st["current_job_id"] = job_id
    st["jobs"][job_id] = job_data
    
    # Списываем монеты
    st["coins"] -= cost
    
    log.info(f"Started job {job_id} for user {user_id}, cost: {cost} coins")
    return job_id

def on_success(user_id: int, job_id: str):
    """Отметить задачу как успешную"""
    if job_id in user_jobs:
        user_jobs[job_id]["status"] = "completed"
        user_jobs[job_id]["completed_at"] = datetime.now()
        
        st = get_user_state(user_id)
        if job_id in st["jobs"]:
            st["jobs"][job_id]["status"] = "completed"
            st["jobs"][job_id]["completed_at"] = datetime.now()
        
        log.info(f"Job {job_id} completed successfully for user {user_id}")

def on_error(user_id: int, job_id: str, reason: str = "unknown_error"):
    """Отметить задачу как неуспешную"""
    if job_id in user_jobs:
        user_jobs[job_id]["status"] = "failed"
        user_jobs[job_id]["error_reason"] = reason
        user_jobs[job_id]["failed_at"] = datetime.now()
        
        st = get_user_state(user_id)
        if job_id in st["jobs"]:
            st["jobs"][job_id]["status"] = "failed"
            st["jobs"][job_id]["error_reason"] = reason
            st["jobs"][job_id]["failed_at"] = datetime.now()
        
        log.error(f"Job {job_id} failed for user {user_id}: {reason}")

def retry(user_id: int, job_id: str) -> bool:
    """Повторить задачу"""
    st = get_user_state(user_id)
    
    if job_id not in st["jobs"]:
        return False
    
    job_data = st["jobs"][job_id]
    
    # Проверяем лимит попыток
    if job_data.get("retry_count", 0) >= 3:
        return False
    
    # Проверяем, хватает ли монет для ретрая
    retry_cost = get_retry_cost(user_id, job_id)
    if st.get("coins", 0) < retry_cost:
        return False
    
    # Увеличиваем счетчик попыток
    job_data["retry_count"] = job_data.get("retry_count", 0) + 1
    job_data["status"] = "processing"
    
    # Списываем монеты за ретрай
    st["coins"] -= retry_cost
    
    log.info(f"Retrying job {job_id} for user {user_id}, attempt {job_data['retry_count']}")
    return True

def can_retry(user_id: int, job_id: str) -> bool:
    """Проверить, можно ли повторить задачу"""
    st = get_user_state(user_id)
    
    if job_id not in st["jobs"]:
        return False
    
    job_data = st["jobs"][job_id]
    
    # Проверяем лимит попыток
    if job_data.get("retry_count", 0) >= 3:
        return False
    
    # Проверяем, хватает ли монет
    retry_cost = get_retry_cost(user_id, job_id)
    return st.get("coins", 0) >= retry_cost

def get_retry_cost(user_id: int, job_id: str) -> int:
    """Получить стоимость ретрая"""
    st = get_user_state(user_id)
    
    if job_id not in st["jobs"]:
        return 1
    
    job_data = st["jobs"][job_id]
    original_cost = job_data.get("coin_cost", 1)
    
    # Ретрай стоит половину от оригинальной стоимости
    return max(1, original_cost // 2)

def check_low_coins(user_id: int) -> bool:
    """Проверить, низкий ли баланс монет"""
    try:
        from app.services.billing import check_subscription
        subscription_data = check_subscription(user_id)
        coins = subscription_data.get("coins", 0)
        is_low = coins < 20  # Считаем низким баланс меньше 20 монет
        log.info(f"[CheckLowCoins] user_id={user_id} coins={coins} is_low={is_low} source=db")
        return is_low
    except Exception as e:
        log.warning(f"Failed to check low coins for user {user_id}: {e}")
        return True  # При ошибке считаем баланс низким

def can_generate_video(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать видео"""
    return can_spend(user_id, "video_8s_audio") or can_spend(user_id, "video_8s_mute")

def can_generate_transform(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать трансформации"""
    return can_spend(user_id, "transform")

def can_use_tryon(user_id: int) -> bool:
    """Проверить, может ли пользователь использовать виртуальную примерочную"""
    return can_spend(user_id, "tryon")

def get_user_coins(user_id: int) -> int:
    """Получить количество монет пользователя"""
    try:
        from app.services.billing import check_subscription
        subscription_data = check_subscription(user_id)
        coins = subscription_data.get("coins", 0)
        log.info(f"[GetUserCoins] user_id={user_id} coins={coins} source=db")
        return coins
    except Exception as e:
        log.warning(f"Failed to get coins for user {user_id}: {e}")
        return 0

def add_coins(user_id: int, amount: int) -> bool:
    """Добавить монеты пользователю"""
    try:
        from app.db.queries import db_manager
        
        # Получаем текущий баланс
        user = db_manager.get_user(user_id)
        if not user:
            # Создаем пользователя если его нет
            user = db_manager.create_user(user_id)
        
        # Добавляем монеты в базу данных
        success = db_manager.add_coins(user_id, amount)
        
        if success:
            new_balance = user.balance + amount
            log.info(f"[AddCoins] user_id={user_id} added={amount} new_balance={new_balance} source=db")
        else:
            log.error(f"Failed to add coins to user {user_id}")
            
        return success
    except Exception as e:
        log.error(f"Failed to add coins to user {user_id}: {e}")
        return False

def spend_coins(user_id: int, amount: int) -> bool:
    """Потратить монеты пользователя"""
    try:
        from app.db.queries import db_manager
        
        # Получаем текущий баланс
        user = db_manager.get_user(user_id)
        if not user:
            log.warning(f"User {user_id} not found for spending coins")
            return False
        
        # Проверяем, хватает ли монет
        if user.balance < amount:
            log.warning(f"Insufficient coins for user {user_id}: {user.balance} < {amount}")
            return False
        
        # Списываем монеты в базе данных
        success = db_manager.spend_coins(user_id, amount, "manual_spend")
        
        if success:
            new_balance = user.balance - amount
            log.info(f"[SpendCoins] user_id={user_id} spent={amount} new_balance={new_balance} source=db")
        else:
            log.error(f"Failed to spend coins from user {user_id}")
            
        return success
    except Exception as e:
        log.error(f"Failed to spend coins from user {user_id}: {e}")
        return False

# Дополнительные функции для совместимости
def can_generate_photo(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать фото"""
    return can_spend(user_id, "transform")

def can_generate_tryon(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать виртуальную примерочную"""
    return can_spend(user_id, "tryon")

def has_active_subscription(user_id: int) -> bool:
    """Проверить, есть ли у пользователя активная подписка"""
    try:
        subscription_data = check_subscription(user_id)
        is_active = subscription_data.get("is_active", False)
        
        # Дополнительно проверяем срок действия
        expires_at = subscription_data.get("expires_at")
        if expires_at:
            from datetime import datetime
            if datetime.now() > expires_at:
                log.warning(f"[HasActiveSubscription] user_id={user_id} subscription expired")
                return False
        
        log.info(f"[HasActiveSubscription] user_id={user_id} active={is_active} expires={expires_at}")
        return is_active
    except Exception as e:
        log.warning(f"Failed to check active subscription for user {user_id}: {e}")
        return False

def can_use_feature(user_id: int, feature_key: str, custom_cost: int = None) -> Dict[str, Any]:
    """
    Единая функция проверки доступа к функциям
    Возвращает подробную информацию о статусе доступа
    
    Args:
        user_id: ID пользователя
        feature_key: Ключ функции
        custom_cost: Пользовательская стоимость (если None, берется из конфига)
    """
    try:
        # Проверяем активную подписку
        subscription_data = check_subscription(user_id)
        is_active = subscription_data.get("is_active", False)
        expires_at = subscription_data.get("expires_at")
        
        # Логируем для отладки
        print(f"[BILLING] can_use_feature user_id={user_id} is_active={is_active} expires_at={expires_at} subscription_data={subscription_data}")
        
        # Монетки доступны даже при истечении подписки
        # Проверяем только баланс монеток
        
        # Проверяем баланс монет
        from app.services.billing import check_subscription
        subscription_data = check_subscription(user_id)
        current_balance = subscription_data.get("coins", 0)
        cost = custom_cost if custom_cost is not None else feature_cost_coins(feature_key)
        
        if current_balance < cost:
            return {
                "can_use": False,
                "reason": "insufficient_coins",
                "message": f"❌ Недостаточно монеток. Нужно: {cost}, у вас: {current_balance}",
                "subscription_data": subscription_data,
                "balance": current_balance,
                "cost": cost
            }
        
        # Все проверки пройдены
        return {
            "can_use": True,
            "reason": "success",
            "message": "✅ Доступ разрешен",
            "subscription_data": subscription_data,
            "balance": current_balance,
            "cost": cost
        }
        
    except Exception as e:
        log.error(f"Failed to check feature access for user {user_id}: {e}")
        return {
            "can_use": False,
            "reason": "error",
            "message": "❌ Ошибка проверки доступа. Попробуйте позже.",
            "error": str(e)
        }

def can_generate_json(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать JSON"""
    return can_spend(user_id, "json")

def activate_plan(user_id: int, plan_name: str) -> bool:
    """Активировать план для пользователя"""
    try:
        from app.db import db_subscriptions as db
        from app.services.pricing import get_available_tariffs
        
        # Получаем информацию о тарифе из конфигурации
        tariffs = get_available_tariffs()
        tariff_info = tariffs.get(plan_name, {})
        
        if not tariff_info:
            log.error(f"Unknown plan {plan_name} for user {user_id}")
            return False
        
        # Активируем план в базе данных
        success = db.activate_user_plan(user_id, plan_name, tariff_info.get("coins", 0))
        
        if success:
            log.info(f"[ActivatePlan] user_id={user_id} plan={plan_name} coins={tariff_info.get('coins', 0)} source=db")
        else:
            log.error(f"Failed to activate plan {plan_name} for user {user_id}")
            
        return success
    except Exception as e:
        log.error(f"Failed to activate plan {plan_name} for user {user_id}: {e}")
        return False

def apply_top_up(user_id: int, coins: int) -> bool:
    """Применить пополнение монет"""
    return add_coins(user_id, coins)

def check_subscription(user_id: int):
    """Проверка активной подписки и получение полной информации о пользователе"""
    try:
        from app.db import db_subscriptions as db
        from app.services.pricing import get_available_tariffs
        
        # Получаем данные из базы данных
        plan_data = db.get_user_plan(user_id)
        
        # Получаем актуальные тарифы из конфигурации
        tariffs = get_available_tariffs()
        plan_name = plan_data.get("plan", "lite")
        
        # Получаем информацию о тарифе из конфигурации (tariffs - это список)
        tariff_info = next((t for t in tariffs if t["name"] == plan_name), {})
        coins_from_tariff = tariff_info.get("coins", 0) if tariff_info else 0
        
        # Используем монеты из базы данных, если они есть, иначе из тарифа
        coins = plan_data.get("coins", coins_from_tariff)
        
        # Логируем источник данных
        log.info(f"[SubscriptionCheck] user_id={user_id} plan={plan_name} coins={coins} source=db")
        
        # Возвращаем полную информацию о пользователе
        return {
            "user_id": user_id,
            "plan": plan_name,
            "coins": coins,
            "expires_at": plan_data.get("expiry"),
            "is_active": plan_data.get("is_active", False),
            "source": "db"  # Указываем источник данных
        }
        
    except Exception as e:
        log.warning(f"Failed to check subscription for user {user_id}: {e}")
        # Возвращаем дефолтные значения при ошибке
        return {
            "user_id": user_id,
            "plan": "lite",
            "coins": 0,
            "expires_at": None,
            "is_active": False,
            "source": "error"
        }

def check_and_reset_expired_plans():
    """
    Проверяет истёкшие подписки, сбрасывает их и записывает логи.
    """
    print("🔄 Проверка истекших подписок начата...")
    now = datetime.utcnow()

    try:
        from app.db import db_subscriptions as db_sub
        with db_sub.db_conn() as conn:
            cur = conn.cursor()
            
            # Определяем тип базы данных
            is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
            
            # Находим пользователей с истёкшими подписками
            if is_postgres:
                cur.execute("""
                    SELECT user_id, plan, end_date
                    FROM subscriptions
                    WHERE end_date IS NOT NULL AND end_date < %s AND is_active = TRUE;
                """, (now,))
            else:
                cur.execute("""
                    SELECT user_id, plan, end_date
                    FROM subscriptions
                    WHERE end_date IS NOT NULL AND end_date < ? AND is_active = 1;
                """, (now,))
            
            expired = cur.fetchall()

            if not expired:
                print("✅ Нет истекших подписок.")
                return []

            expired_users = [row[0] for row in expired]
            
            # Деактивируем подписки
            if is_postgres:
                cur.execute("""
                    UPDATE subscriptions
                    SET is_active = FALSE, updated_at = %s
                    WHERE user_id = ANY(%s);
                """, (now, expired_users))
            else:
                # Для SQLite используем IN вместо ANY
                placeholders = ','.join(['?' for _ in expired_users])
                cur.execute(f"""
                    UPDATE subscriptions
                    SET is_active = 0, updated_at = ?
                    WHERE user_id IN ({placeholders});
                """, [now] + expired_users)

            # Переводим на free план, но СОХРАНЯЕМ монетки
            if is_postgres:
                cur.execute("""
                    UPDATE users
                    SET plan = 'free', updated_at = %s
                    WHERE user_id = ANY(%s);
                """, (now, expired_users))
            else:
                placeholders = ','.join(['?' for _ in expired_users])
                cur.execute(f"""
                    UPDATE users
                    SET plan = 'free', updated_at = ?
                    WHERE user_id IN ({placeholders});
                """, [now] + expired_users)

            # Логируем транзакции для каждого пользователя
            for user_id in expired_users:
                if is_postgres:
                    cur.execute("""
                        INSERT INTO transactions (user_id, feature, coins_spent, note, timestamp)
                        VALUES (%s, 'subscription_expired', 0, 'Subscription expired, plan reset to free (coins preserved)', %s);
                    """, (user_id, now))
                else:
                    cur.execute("""
                        INSERT INTO transactions (user_id, feature, coins_spent, note, timestamp)
                        VALUES (?, 'subscription_expired', 0, 'Subscription expired, plan reset to free (coins preserved)', ?);
                    """, (user_id, now))

            conn.commit()

        print(f"⚠️ {len(expired_users)} подписок истекло, план сброшен на free (монетки сохранены): {expired_users}")
        return expired_users
        
    except Exception as e:
        log.error(f"Failed to check and reset expired plans: {e}")
        print(f"❌ Ошибка при проверке истекших подписок: {e}")
        return []
