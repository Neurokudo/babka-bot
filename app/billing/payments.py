# -*- coding: utf-8 -*-
"""
app/billing/payments.py - Обработка платежей и вебхуков (финальная версия)
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from app.db.queries import db
from app.config.pricing import TARIFFS, TOPUP_PACKS_RUB
from app.billing.plans import activate_plan
from app.billing.coins import add_coins

log = logging.getLogger("billing.payments")


def create_payment_record(
    user_id: int,
    subscription_type: str,
    amount: float,
    idempotent_key: Optional[str] = None
) -> str:
    """
    Создает запись о платеже в БД
    
    Returns:
        UUID платежа
    """
    payment_id = str(uuid.uuid4())
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO payments (id, user_id, subscription_type, amount, status, idempotent_key)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    payment_id,
                    user_id,
                    subscription_type,
                    amount,
                    "pending",
                    idempotent_key
                )
            )
            
            db.connection.commit()
            log.info(f"Created payment record {payment_id} for {subscription_type}")
            return payment_id
            
    except Exception as e:
        log.error(f"Failed to create payment record: {e}")
        raise


def update_payment_status(
    payment_id: str,
    status: str
) -> bool:
    """
    Обновляет статус платежа
    
    Returns:
        True если обновление прошло успешно
    """
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE payments SET status = %s WHERE id = %s",
                (status, payment_id)
            )
            
            db.connection.commit()
            log.info(f"Updated payment {payment_id} status to {status}")
            return True
            
    except Exception as e:
        log.error(f"Failed to update payment status: {e}")
        return False


def process_payment_success(
    payment_id: str,
    user_id: int,
    subscription_type: str
) -> bool:
    """
    Обрабатывает успешный платеж
    
    Args:
        payment_id: UUID платежа
        user_id: ID пользователя
        subscription_type: тип подписки/продукта
    
    Returns:
        True если обработка прошла успешно
    """
    try:
        with db.connection.cursor() as cursor:
            # Получаем данные платежа
            cursor.execute(
                "SELECT * FROM payments WHERE id = %s",
                (payment_id,)
            )
            payment = cursor.fetchone()
            
            if not payment:
                log.error(f"Payment {payment_id} not found")
                return False
            
            # Обрабатываем в зависимости от типа продукта
            if subscription_type in TARIFFS:
                # Активируем план
                user_data = activate_plan(user_id, subscription_type)
                if not user_data:
                    log.error(f"Failed to activate plan {subscription_type} for user {user_id}")
                    return False
                
                log.info(f"Successfully activated plan {subscription_type} for user {user_id}")
                
            elif subscription_type.startswith("coins_"):
                # Разовое пополнение монет
                coins_amount = int(subscription_type.split("_")[1])
                add_coins(user_id, coins_amount, f"purchase:{subscription_type}")
                log.info(f"Successfully added {coins_amount} coins to user {user_id}")
                
            else:
                log.error(f"Unknown subscription type: {subscription_type}")
                return False
            
            # Обновляем статус платежа
            update_payment_status(payment_id, "succeeded")
            return True
            
    except Exception as e:
        log.error(f"Failed to process payment success: {e}")
        return False


def process_payment_failure(payment_id: str, reason: str = "failed") -> bool:
    """
    Обрабатывает неудачный платеж
    
    Returns:
        True если обработка прошла успешно
    """
    try:
        update_payment_status(payment_id, reason)
        log.info(f"Payment {payment_id} marked as {reason}")
        return True
        
    except Exception as e:
        log.error(f"Failed to process payment failure: {e}")
        return False


def is_payment_processed(payment_id: str) -> bool:
    """
    Проверяет, был ли платеж уже обработан
    
    Returns:
        True если платеж уже обработан
    """
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM payments WHERE id = %s",
                (payment_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return False
            
            status = result[0]
            return status in ["succeeded", "failed", "canceled"]
            
    except Exception as e:
        log.error(f"Failed to check payment status: {e}")
        return False


def get_payment_by_idempotent_key(idempotent_key: str) -> Optional[Dict[str, Any]]:
    """
    Получает платеж по ключу идемпотентности
    
    Returns:
        Данные платежа или None
    """
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM payments WHERE idempotent_key = %s",
                (idempotent_key,)
            )
            result = cursor.fetchone()
            
            if not result:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
            
    except Exception as e:
        log.error(f"Failed to get payment by idempotent key: {e}")
        return None


def validate_webhook_signature(
    payload: str,
    signature: str,
    secret: str
) -> bool:
    """
    Валидирует подпись вебхука (заглушка для YooKassa)
    
    В реальной реализации здесь должна быть проверка HMAC-SHA256
    """
    # TODO: Реализовать проверку подписи для YooKassa
    return True


def process_yookassa_webhook(webhook_data: Dict[str, Any]) -> bool:
    """
    Обрабатывает вебхук от YooKassa
    
    Args:
        webhook_data: Данные вебхука
    
    Returns:
        True если обработка прошла успешно
    """
    try:
        event = webhook_data.get("event")
        if event != "payment.succeeded":
            log.info(f"Ignoring webhook event: {event}")
            return True
        
        payment_data = webhook_data.get("object", {})
        payment_id = payment_data.get("id")
        amount = float(payment_data.get("amount", {}).get("value", 0))
        metadata = payment_data.get("metadata", {})
        
        user_id = int(metadata.get("user_id", 0))
        subscription_type = metadata.get("subscription_type", "")
        idempotent_key = metadata.get("idempotent_key", "")
        
        if not user_id or not subscription_type:
            log.error(f"Missing user_id or subscription_type in webhook: {webhook_data}")
            return False
        
        # Проверяем идемпотентность
        if idempotent_key:
            existing_payment = get_payment_by_idempotent_key(idempotent_key)
            if existing_payment:
                log.info(f"Payment with idempotent key {idempotent_key} already processed")
                return True
        
        # Создаем запись о платеже
        payment_record_id = create_payment_record(
            user_id=user_id,
            subscription_type=subscription_type,
            amount=amount,
            idempotent_key=idempotent_key
        )
        
        # Обрабатываем успешный платеж
        success = process_payment_success(
            payment_id=payment_record_id,
            user_id=user_id,
            subscription_type=subscription_type
        )
        
        if success:
            log.info(f"Successfully processed YooKassa payment {payment_id} for user {user_id}")
        else:
            log.error(f"Failed to process YooKassa payment {payment_id} for user {user_id}")
        
        return success
        
    except Exception as e:
        log.error(f"Failed to process YooKassa webhook: {e}")
        return False