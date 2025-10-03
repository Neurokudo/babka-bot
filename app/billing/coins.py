# -*- coding: utf-8 -*-
"""
app/billing/coins.py - Атомарные операции с монетами (финальная версия)
"""

import logging
from typing import Optional

from app.db.queries import db

# Админ ID (перенесен из старого конфига)
ADMIN_ID = 5015100177

log = logging.getLogger("billing.coins")


class InsufficientFunds(Exception):
    """Недостаточно средств"""
    pass


def atomic_spend_coins(user_id: int, cost: int, operation_type: str) -> Optional[int]:
    """
    Атомарно списывает монеты с пользователя
    
    Args:
        user_id: ID пользователя
        cost: количество монет для списания
        operation_type: тип операции (video, photo, tryon, json, etc.)
    
    Returns:
        ID транзакции или None если недостаточно средств
    """
    if cost <= 0:
        raise ValueError("Cost must be positive")
    
    try:
        with db.connection.cursor() as cursor:
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
                INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id
                """,
                (user_id, operation_type, cost)
            )
            
            transaction_id = cursor.fetchone()[0]
            db.connection.commit()
            
            log.info(f"Spent {cost} coins for user {user_id}, transaction {transaction_id}")
            return transaction_id
            
    except Exception as e:
        log.error(f"Failed to spend coins for user {user_id}: {e}")
        return None


def add_coins(user_id: int, amount: int, reason: str) -> int:
    """
    Атомарно добавляет монеты пользователю
    
    Args:
        user_id: ID пользователя
        amount: количество монет для добавления
        reason: причина начисления (welcome, plan:standard, purchase:coins100, etc.)
    
    Returns:
        Новый баланс монет
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    try:
        with db.connection.cursor() as cursor:
            # Получаем текущий баланс
            cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                # Создаем пользователя если его нет
                cursor.execute(
                    "INSERT INTO users (user_id, coins) VALUES (%s, %s)",
                    (user_id, amount)
                )
                after_coins = amount
            else:
                before_coins = result[0]
                after_coins = before_coins + amount
                
                # Обновляем баланс
                cursor.execute(
                    "UPDATE users SET coins = coins + %s, updated_at = NOW() WHERE user_id = %s",
                    (amount, user_id)
                )
            
            # Записываем транзакцию для начисления
            cursor.execute(
                """
                INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                VALUES (%s, %s, %s, 'completed')
                """,
                (user_id, reason, amount)
            )
            
            log.info(f"Added {amount} coins to user {user_id}, reason: {reason}")
            db.connection.commit()
            return after_coins
            
    except Exception as e:
        log.error(f"Failed to add coins to user {user_id}: {e}")
        raise


def get_balance(user_id: int) -> int:
    """Получает текущий баланс монет пользователя"""
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        log.error(f"Failed to get balance for user {user_id}: {e}")
        return 0


def can_afford(user_id: int, cost: int) -> bool:
    """Проверяет, может ли пользователь позволить себе операцию"""
    return get_balance(user_id) >= cost


def add_admin_coins(user_id: int, amount: int, reason: str) -> int:
    """
    Добавляет админские монеты (только для админа)
    """
    if user_id != ADMIN_ID:
        raise ValueError("Admin coins can only be added to admin user")
    
    try:
        with db.connection.cursor() as cursor:
            # Получаем текущий баланс админских монет
            cursor.execute("SELECT admin_coins FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Admin user not found")
            
            before_coins = result[0]
            after_coins = before_coins + amount
            
            # Обновляем баланс
            cursor.execute(
                "UPDATE users SET admin_coins = admin_coins + %s, updated_at = NOW() WHERE user_id = %s",
                (amount, user_id)
            )
            
            log.info(f"Added {amount} admin coins to user {user_id}, reason: {reason}")
            db.connection.commit()
            return after_coins
            
    except Exception as e:
        log.error(f"Failed to add admin coins to user {user_id}: {e}")
        raise


def get_admin_balance(user_id: int) -> int:
    """Получает баланс админских монет"""
    if user_id != ADMIN_ID:
        return 0
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT admin_coins FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        log.error(f"Failed to get admin balance for user {user_id}: {e}")
        return 0


def update_transaction_status(transaction_id: int, status: str) -> bool:
    """Обновляет статус транзакции"""
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE transactions SET status = %s WHERE id = %s",
                (status, transaction_id)
            )
            db.connection.commit()
            return True
    except Exception as e:
        log.error(f"Failed to update transaction status: {e}")
        return False


def refund_coins(user_id: int, amount: int, original_transaction_id: Optional[int] = None) -> Optional[int]:
    """Возвращает монеты пользователю"""
    try:
        with db.connection.cursor() as cursor:
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
                INSERT INTO transactions (user_id, operation_type, coins_spent, status)
                VALUES (%s, %s, %s, 'refunded')
                RETURNING id
                """,
                (user_id, f"refund{'_' + str(original_transaction_id) if original_transaction_id else ''}", amount)
            )
            
            transaction_id = cursor.fetchone()[0]
            db.connection.commit()
            
            log.info(f"Refunded {amount} coins to user {user_id}, transaction {transaction_id}")
            return transaction_id
            
    except Exception as e:
        log.error(f"Failed to refund coins to user {user_id}: {e}")
        return None