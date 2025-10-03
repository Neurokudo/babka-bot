# -*- coding: utf-8 -*-
"""
app/billing/plans.py - Управление подписками и планами (финальная версия)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.db.queries import db
from app.services.pricing import get_available_tariffs
from app.billing.coins import add_coins

# Админ ID (перенесен из старого конфига)
ADMIN_ID = 5015100177

log = logging.getLogger("billing.plans")


def check_subscription(user_id: int) -> Dict[str, Any]:
    """
    Проверяет срок действия тарифа и при необходимости сбрасывает его на lite
    
    Returns:
        Обновленные данные пользователя
    """
    try:
        with db.connection.cursor() as cursor:
            # Получаем данные пользователя
            cursor.execute(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                # Создаем пользователя если его нет
                cursor.execute(
                    """
                    INSERT INTO users (user_id, coins, plan, plan_expiry, admin_coins)
                    VALUES (%s, 0, 'lite', NULL, 0)
                    """,
                    (user_id,)
                )
                db.connection.commit()
                
                return {
                    "user_id": user_id,
                    "coins": 0,
                    "plan": "lite",
                    "plan_expiry": None,
                    "admin_coins": 0
                }
            
            # Проверяем план
            columns = [desc[0] for desc in cursor.description]
            user_data = dict(zip(columns, result))
            
            plan = user_data.get("plan", "lite")
            plan_expiry = user_data.get("plan_expiry")
            
            # Если план не lite и истек - сбрасываем
            if plan != "lite" and plan_expiry:
                try:
                    expiry_dt = plan_expiry if isinstance(plan_expiry, datetime) else datetime.fromisoformat(str(plan_expiry).replace("Z", "+00:00"))
                    if expiry_dt < datetime.now(timezone.utc):
                        cursor.execute(
                            """
                            UPDATE users 
                            SET plan = 'lite', plan_expiry = NULL, updated_at = NOW()
                            WHERE user_id = %s
                            """,
                            (user_id,)
                        )
                        user_data["plan"] = "lite"
                        user_data["plan_expiry"] = None
                        db.connection.commit()
                        log.info(f"Reset expired plan for user {user_id}")
                except Exception as e:
                    log.error(f"Failed to parse plan_expiry for user {user_id}: {e}")
            
            return user_data
            
    except Exception as e:
        log.error(f"Failed to check subscription for user {user_id}: {e}")
        return {"user_id": user_id, "coins": 0, "plan": "lite", "plan_expiry": None, "admin_coins": 0}


def activate_plan(user_id: int, plan_key: str) -> Optional[Dict[str, Any]]:
    """
    Активирует план для пользователя
    
    Args:
        user_id: ID пользователя
        plan_key: ключ плана (lite, standard, pro)
    
    Returns:
        Обновленные данные пользователя или None если план не найден
    """
    tariffs = get_available_tariffs()
    tariff = tariffs.get(plan_key)
    if not tariff:
        log.error(f"Unknown plan: {plan_key}")
        return None
    
    try:
        # Сначала проверяем подписку
        user_data = check_subscription(user_id)
        
        with db.connection.cursor() as cursor:
            # Начисляем монеты за план
            coins_to_add = tariff["coins"]
            add_coins(user_id, coins_to_add, f"plan:{plan_key}")
            
            # Устанавливаем план и срок действия
            if plan_key == "lite":
                plan_expiry = None
            else:
                now = datetime.now(timezone.utc)
                if user_data.get("plan_expiry") and user_data["plan_expiry"] > now:
                    # Продлеваем существующую подписку
                    plan_expiry = user_data["plan_expiry"] + timedelta(days=30)
                else:
                    # Новая подписка
                    plan_expiry = now + timedelta(days=30)
            
            # Обновляем план в БД
            cursor.execute(
                """
                UPDATE users 
                SET plan = %s, plan_expiry = %s, updated_at = NOW()
                WHERE user_id = %s
                """,
                (plan_key, plan_expiry, user_id)
            )
            
            # Обновляем данные пользователя
            user_data["plan"] = plan_key
            user_data["plan_expiry"] = plan_expiry
            user_data["coins"] += coins_to_add
            
            db.connection.commit()
            log.info(f"Activated plan {plan_key} for user {user_id}, added {coins_to_add} coins")
            return user_data
            
    except Exception as e:
        log.error(f"Failed to activate plan {plan_key} for user {user_id}: {e}")
        return None


def check_and_reset_expired_plans() -> list[int]:
    """
    Проверяет и сбрасывает истекшие планы
    
    Returns:
        Список ID пользователей, у которых был сброшен план
    """
    reset_users = []
    
    try:
        with db.connection.cursor() as cursor:
            # Находим пользователей с истекшими планами
            cursor.execute(
                """
                SELECT user_id FROM users 
                WHERE plan != 'lite' 
                AND plan_expiry IS NOT NULL 
                AND plan_expiry < NOW()
                """
            )
            expired_users = cursor.fetchall()
            
            for (user_id,) in expired_users:
                # Сбрасываем план на lite
                cursor.execute(
                    """
                    UPDATE users 
                    SET plan = 'lite', plan_expiry = NULL, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                reset_users.append(user_id)
                log.info(f"Reset expired plan for user {user_id}")
            
            db.connection.commit()
            return reset_users
            
    except Exception as e:
        log.error(f"Failed to check expired plans: {e}")
        return []


def get_user_plan_info(user_id: int) -> Dict[str, Any]:
    """
    Получает информацию о плане пользователя
    
    Returns:
        Словарь с информацией о плане
    """
    try:
        user_data = check_subscription(user_id)
        plan = user_data.get("plan", "lite")
        plan_expiry = user_data.get("plan_expiry")
        
        # Проверяем, активен ли план
        is_active = True
        if plan != "lite" and plan_expiry:
            is_active = plan_expiry > datetime.now(timezone.utc)
        
        return {
            "plan": plan,
            "plan_expiry": plan_expiry,
            "is_active": is_active,
            "plan_info": get_available_tariffs().get(plan)
        }
        
    except Exception as e:
        log.error(f"Failed to get plan info for user {user_id}: {e}")
        return {"plan": "lite", "plan_expiry": None, "is_active": False}


def is_plan_active(user_id: int) -> bool:
    """Проверяет, активен ли план пользователя"""
    plan_info = get_user_plan_info(user_id)
    return plan_info["is_active"]


def get_plan_expiry_text(user_id: int) -> str:
    """Возвращает текстовое описание срока действия плана"""
    plan_info = get_user_plan_info(user_id)
    
    if plan_info["plan"] == "lite":
        return "Бесплатный план"
    
    if not plan_info["is_active"]:
        return "План истек"
    
    if plan_info["plan_expiry"]:
        expiry = plan_info["plan_expiry"]
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        
        days_left = (expiry - datetime.now(timezone.utc)).days
        if days_left > 0:
            return f"Осталось {days_left} дней"
        else:
            return "План истек"
    
    return "План активен"


def give_welcome_bonus(user_id: int) -> bool:
    """
    Выдает стартовые бонусы пользователю (один раз)
    
    Returns:
        True если бонусы были выданы, False если уже были выданы ранее
    """
    try:
        with db.connection.cursor() as cursor:
            # Проверяем, есть ли уже записи о транзакциях пользователя
            cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id = %s AND operation_type = 'welcome_bonus'",
                (user_id,)
            )
            has_welcome = cursor.fetchone()[0] > 0
            
            if has_welcome:
                log.info(f"User {user_id} already received welcome bonus")
                return False
            
            # Выдаем стартовые бонусы
            welcome_coins = 23  # 2 видео (20) + 3 фото (3) = 23 монеты
            add_coins(user_id, welcome_coins, "welcome_bonus")
            
            log.info(f"Gave welcome bonus {welcome_coins} coins to user {user_id}")
            return True
            
    except Exception as e:
        log.error(f"Failed to give welcome bonus to user {user_id}: {e}")
        return False