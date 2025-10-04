"""
Сервис для работы с YooKassa API
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from yookassa import Configuration, Payment

log = logging.getLogger("yookassa_service")

# Глобальная переменная для отслеживания состояния YooKassa
YOOKASSA_ENABLED = False

# Инициализация YooKassa
def init_yookassa():
    """Инициализация YooKassa с боевыми ключами"""
    global YOOKASSA_ENABLED
    
    # Детальная диагностика переменных окружения
    print("ENV KEYS:", [k for k in os.environ.keys() if "YOO" in k])
    print("All env keys:", sorted(os.environ.keys()))
    
    SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
    SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
    
    # Улучшенное форматирование логов
    print(f"DEBUG YOOKASSA ENV → SHOP_ID={SHOP_ID}, SECRET_KEY={'***' if SECRET_KEY else None}")
    
    # Проверяем переменные окружения
    if not SHOP_ID or not SECRET_KEY:
        print("⚠️ YooKassa credentials missing, fallback to sandbox mode")
        log.warning("YooKassa credentials not found in environment variables")
        log.warning(f"SHOP_ID: {SHOP_ID}, SECRET_KEY: {'present' if SECRET_KEY else 'missing'}")
        YOOKASSA_ENABLED = False
        return False
    
    # Проверяем, что ключ начинается с правильного префикса
    if not SECRET_KEY.startswith(("test_", "live_")):
        log.warning(f"SECRET_KEY doesn't start with test_ or live_: {SECRET_KEY[:10]}...")
        YOOKASSA_ENABLED = False
        return False
    
    # Инициализируем YooKassa
    try:
        Configuration.account_id = SHOP_ID
        Configuration.secret_key = SECRET_KEY
        
        log.info(f"YooKassa initialized with shop_id: {SHOP_ID}")
        YOOKASSA_ENABLED = True
        return True
    except Exception as e:
        log.error(f"Failed to initialize YooKassa: {e}")
        YOOKASSA_ENABLED = False
        return False

def create_payment(user_id: int, plan: str, price_rub: int, coins: int, username: str = None) -> Tuple[str, str]:
    """
    Создать платеж в YooKassa
    
    Args:
        user_id: ID пользователя Telegram
        plan: Название тарифа (lite, standard, pro)
        price_rub: Цена в рублях
        coins: Количество монет
        username: Username пользователя (опционально)
    
    Returns:
        Tuple[str, str]: (payment_url, payment_id)
    """
    try:
        # Проверяем, включен ли YooKassa
        if not YOOKASSA_ENABLED:
            raise RuntimeError("YooKassa is not enabled - credentials not found")
        
        # Инициализируем YooKassa если еще не инициализирован
        init_yookassa()
        
        # Формируем описание платежа
        description = f"Покупка подписки '{plan.upper()}' пользователем @{username or user_id}"
        
        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": f"{price_rub}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/babkakudo_bot"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "plan": plan,
                "coins": str(coins),
                "price": str(price_rub),
                "type": "plan"
            }
        })
        
        payment_url = payment.confirmation.confirmation_url
        payment_id = payment.id
        
        log.info(f"Payment created: {payment_id} for user {user_id}, plan {plan}, amount {price_rub} RUB")
        
        return payment_url, payment_id
        
    except Exception as e:
        log.error(f"Failed to create payment for user {user_id}: {e}")
        raise

def create_topup_payment(user_id: int, coins: int, price_rub: int, username: str = None) -> Tuple[str, str]:
    """
    Создать платеж для пополнения монет
    
    Args:
        user_id: ID пользователя Telegram
        coins: Количество монет для пополнения
        price_rub: Цена в рублях
        username: Username пользователя (опционально)
    
    Returns:
        Tuple[str, str]: (payment_url, payment_id)
    """
    try:
        # Инициализируем YooKassa если еще не инициализирован
        init_yookassa()
        
        # Формируем описание платежа
        description = f"Пополнение {coins} монет пользователем @{username or user_id}"
        
        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": f"{price_rub}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/babkakudo_bot"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "coins": str(coins),
                "price": str(price_rub),
                "type": "topup"
            }
        })
        
        payment_url = payment.confirmation.confirmation_url
        payment_id = payment.id
        
        log.info(f"Topup payment created: {payment_id} for user {user_id}, coins {coins}, amount {price_rub} RUB")
        
        return payment_url, payment_id
        
    except Exception as e:
        log.error(f"Failed to create topup payment for user {user_id}: {e}")
        raise

def check_payment_status(payment_id: str) -> Dict[str, Any]:
    """
    Проверить статус платежа
    
    Args:
        payment_id: ID платежа в YooKassa
    
    Returns:
        Dict с информацией о платеже
    """
    try:
        init_yookassa()
        
        payment = Payment.find_one(payment_id)
        
        result = {
            "payment_id": payment_id,
            "status": payment.status,
            "amount": float(payment.amount.value),
            "currency": payment.amount.currency,
            "description": payment.description,
            "metadata": payment.metadata or {},
            "created_at": payment.created_at,
            "paid": payment.paid
        }
        
        log.info(f"Payment {payment_id} status: {payment.status}")
        return result
        
    except Exception as e:
        log.error(f"Failed to check payment status for {payment_id}: {e}")
        return {
            "payment_id": payment_id,
            "status": "error",
            "error": str(e)
        }

def process_payment_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обработать webhook от YooKassa
    
    Args:
        webhook_data: Данные webhook от YooKassa
    
    Returns:
        Dict с обработанными данными или None если webhook не поддерживается
    """
    try:
        event_type = webhook_data.get("event")
        payment_data = webhook_data.get("object", {})
        
        if event_type not in ["payment.succeeded", "payment.canceled", "payment.waiting_for_capture"]:
            log.info(f"Unsupported webhook event: {event_type}")
            return None
        
        # Извлекаем данные платежа
        payment_id = payment_data.get("id")
        status = payment_data.get("status")
        amount = payment_data.get("amount", {})
        metadata = payment_data.get("metadata", {})
        
        # Проверяем, что это наш платеж
        if not metadata.get("user_id"):
            log.warning(f"Payment {payment_id} has no user_id in metadata")
            return None
        
        result = {
            "event": event_type,
            "payment_id": payment_id,
            "status": status,
            "user_id": int(metadata.get("user_id", 0)),
            "amount": float(amount.get("value", 0)),
            "currency": amount.get("currency", "RUB"),
            "metadata": metadata,
            "description": payment_data.get("description", "")
        }
        
        log.info(f"Processed webhook: {event_type} for payment {payment_id}, user {result['user_id']}")
        return result
        
    except Exception as e:
        log.error(f"Failed to process webhook: {e}")
        return None

def process_successful_payment(payment_data: Dict[str, Any]) -> bool:
    """
    Обработать успешный платеж и создать подписку/пополнить баланс
    
    Args:
        payment_data: Данные платежа из webhook
    
    Returns:
        bool: True если платеж обработан успешно
    """
    try:
        user_id = payment_data.get("user_id", 0)
        amount = payment_data.get("amount", 0)
        metadata = payment_data.get("metadata", {})
        payment_id = payment_data.get("payment_id", "")
        
        if not user_id:
            log.error("No user_id in payment data")
            return False
        
        # Импортируем функции базы данных
        from app.db import db_subscriptions as db
        
        if metadata.get("type") == "plan":
            # Создаем подписку
            plan = metadata.get("plan", "lite")
            coins = int(metadata.get("coins", 0))
            price_rub = int(metadata.get("price", 0))
            
            # Получаем информацию о тарифе
            from app.services.pricing import get_tariff_by_name
            plan_info = get_tariff_by_name(plan)
            
            if plan_info:
                db.create_subscription(
                    user_id=user_id,
                    plan=plan,
                    coins=coins,
                    price_rub=price_rub,
                    duration_days=30,
                    payment_id=payment_id
                )
                log.info(f"Subscription created for user {user_id}: {plan} plan, {coins} coins")
                return True
            else:
                log.error(f"Plan info not found for {plan}")
                return False
        
        elif metadata.get("type") == "topup":
            # Пополнение монет
            coins = int(metadata.get("coins", 0))
            if coins > 0:
                # Создаем пользователя если его нет
                db.create_or_update_user(user_id)
                
                # Добавляем монеты к существующему балансу
                current_balance = db.get_user_balance(user_id)
                new_balance = current_balance + coins
                
                # Обновляем баланс пользователя
                with db.db_conn() as conn:
                    cur = conn.cursor()
                    is_postgres = hasattr(conn, 'cursor') and 'psycopg2' in str(type(conn))
                    if is_postgres:
                        cur.execute("UPDATE users SET coins = %s WHERE user_id = %s", (new_balance, user_id))
                    else:
                        cur.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_balance, user_id))
                    conn.commit()
                
                # Записываем транзакцию
                db.charge_feature(user_id, "topup", 0, f"Topup: +{coins} coins via payment {payment_id}")
                
                log.info(f"Topup processed for user {user_id}: +{coins} coins")
                return True
        
        log.warning(f"Unknown payment type: {metadata.get('type')}")
        return False
        
    except Exception as e:
        log.error(f"Error processing successful payment: {e}")
        return False

# Инициализируем YooKassa при импорте модуля
try:
    if init_yookassa():
        log.info("YooKassa service initialized successfully")
    else:
        log.warning("YooKassa service initialization skipped - credentials not found")
except Exception as e:
    log.warning(f"YooKassa initialization failed: {e}")
