"""
Централизованный менеджер баланса для всех монетных операций
Единая точка управления всеми операциями с монетами с автоматическим аудитом
"""

from app.db import db_subscriptions as db
from app.services import billing_observer
import logging
from typing import Optional

log = logging.getLogger("babka-bot")

class InsufficientFundsError(Exception):
    """Исключение при недостатке средств"""
    pass

def get_balance(user_id: int) -> int:
    """Получить текущий баланс пользователя"""
    try:
        return db.get_user_balance(user_id)
    except Exception as e:
        log.error(f"Failed to get balance for user {user_id}: {e}")
        return 0

def add_coins(user_id: int, amount: int, reason: str, feature: str = None) -> int:
    """
    Добавить монеты пользователю
    
    Args:
        user_id: ID пользователя
        amount: Количество монет для добавления
        reason: Причина добавления (например, "subscription_payment", "bonus_gift")
        feature: Тип функции/операции (например, "subscription_lite", "manual_add")
    
    Returns:
        Новый баланс пользователя
    """
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    
    try:
        old_balance = db.get_user_balance(user_id)
        success = db.update_user_balance(user_id, amount, note=reason)
        
        if not success:
            raise Exception("Failed to update balance in database")
        
        new_balance = old_balance + amount
        
        # Логируем операцию в аудит
        billing_observer.log(
            user_id=user_id,
            delta=amount,
            feature=feature,
            reason=reason,
            old_balance=old_balance,
            new_balance=new_balance
        )
        
        log.info(f"[BALANCE +] uid={user_id} +{amount} → {new_balance} ({reason})")
        return new_balance
        
    except Exception as e:
        log.error(f"Failed to add coins for user {user_id}: {e}")
        raise

def spend_coins(user_id: int, amount: int, reason: str, feature: str = None) -> int:
    """
    Потратить монеты пользователя
    
    Args:
        user_id: ID пользователя
        amount: Количество монет для списания
        reason: Причина списания (например, "video_generation", "photo_edit")
        feature: Тип функции/операции (например, "video_8s_audio", "image_basic")
    
    Returns:
        Новый баланс пользователя
        
    Raises:
        InsufficientFundsError: Если недостаточно средств
    """
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    
    try:
        old_balance = db.get_user_balance(user_id)
        
        if old_balance < amount:
            raise InsufficientFundsError(f"Insufficient funds: {old_balance} < {amount}")
        
        success = db.charge_feature(user_id, feature or "unknown", amount, note=reason)
        
        if not success:
            raise Exception("Failed to charge feature in database")
        
        new_balance = old_balance - amount
        
        # Логируем операцию в аудит
        billing_observer.log(
            user_id=user_id,
            delta=-amount,
            feature=feature,
            reason=reason,
            old_balance=old_balance,
            new_balance=new_balance
        )
        
        log.info(f"[BALANCE -] uid={user_id} -{amount} → {new_balance} ({reason})")
        return new_balance
        
    except InsufficientFundsError:
        raise
    except Exception as e:
        log.error(f"Failed to spend coins for user {user_id}: {e}")
        raise

def set_balance(user_id: int, new_balance: int, reason: str, admin_note: str = None) -> int:
    """
    Установить точный баланс пользователя (админская операция)
    
    Args:
        user_id: ID пользователя
        new_balance: Новый баланс
        reason: Причина изменения
        admin_note: Дополнительная заметка администратора
    
    Returns:
        Новый баланс пользователя
    """
    try:
        old_balance = db.get_user_balance(user_id)
        delta = new_balance - old_balance
        
        if delta == 0:
            log.info(f"[BALANCE =] uid={user_id} balance unchanged: {old_balance}")
            return old_balance
        
        success = db.update_user_balance(user_id, delta, note=reason)
        
        if not success:
            raise Exception("Failed to update balance in database")
        
        # Логируем операцию в аудит
        billing_observer.log(
            user_id=user_id,
            delta=delta,
            feature="admin_set_balance",
            reason=f"{reason} (admin: {admin_note or 'no note'})",
            old_balance=old_balance,
            new_balance=new_balance
        )
        
        log.info(f"[BALANCE =] uid={user_id} {old_balance} → {new_balance} (Δ={delta}) ({reason})")
        return new_balance
        
    except Exception as e:
        log.error(f"Failed to set balance for user {user_id}: {e}")
        raise

def can_afford(user_id: int, amount: int) -> bool:
    """Проверить, может ли пользователь позволить себе операцию"""
    try:
        balance = get_balance(user_id)
        return balance >= amount
    except Exception as e:
        log.error(f"Failed to check affordability for user {user_id}: {e}")
        return False

def get_user_summary(user_id: int) -> dict:
    """Получить сводку по пользователю"""
    try:
        balance = get_balance(user_id)
        recent_transactions = billing_observer.get_user_recent_transactions(user_id, limit=5)
        
        return {
            "user_id": user_id,
            "current_balance": balance,
            "recent_transactions": recent_transactions
        }
    except Exception as e:
        log.error(f"Failed to get user summary for {user_id}: {e}")
        return {
            "user_id": user_id,
            "current_balance": 0,
            "recent_transactions": []
        }
