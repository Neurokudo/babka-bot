# -*- coding: utf-8 -*-
"""
Система тарифов и подписок
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config import PLANS
from database import db

log = logging.getLogger("subscription_system")

def get_plan_info(plan_name: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о тарифе"""
    return PLANS.get(plan_name)

def can_generate_video_with_plan(user: Dict[str, Any]) -> bool:
    """Проверяет, может ли пользователь сгенерировать видео с учетом монеток"""
    # Проверяем только монетки
    from billing import COST_VIDEO, can_spend
    return can_spend(user, COST_VIDEO)

def can_generate_photo_with_plan(user: Dict[str, Any], cost: int = None) -> bool:
    """Проверяет, может ли пользователь сгенерировать фото с учетом монеток"""
    if cost is None:
        from billing import COST_TRANSFORM
        cost = COST_TRANSFORM
    
    # Проверяем только монетки
    from billing import can_spend
    return can_spend(user, cost)

def spend_video_resource(user: Dict[str, Any]) -> bool:
    """Списать монетки за видео"""
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    from billing import COST_VIDEO, can_spend
    if not can_spend(user, COST_VIDEO):
        return False
    
    before_value = user.get("coins", 0)
    user["coins"] -= COST_VIDEO
    after_value = user.get("coins", 0)
    
    # Логируем транзакцию
    db.add_transaction(
        user_id=user_id,
        operation_type="video",
        coins_spent=COST_VIDEO,
        used_bonus=False,
        before_value=before_value,
        after_value=after_value,
        delta=-COST_VIDEO,
        reason="video_spend"
    )
    
    db.save_user(user_id, user)
    return True

def spend_photo_resource(user: Dict[str, Any], cost: int = None) -> bool:
    """Списать монетки за фото"""
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    if cost is None:
        from billing import COST_TRANSFORM
        cost = COST_TRANSFORM
    
    from billing import can_spend
    if not can_spend(user, cost):
        return False
    
    before_value = user.get("coins", 0)
    user["coins"] -= cost
    after_value = user.get("coins", 0)
    
    # Логируем транзакцию
    db.add_transaction(
        user_id=user_id,
        operation_type="transform",
        coins_spent=cost,
        used_bonus=False,
        before_value=before_value,
        after_value=after_value,
        delta=-cost,
        reason="photo_spend"
    )
    
    db.save_user(user_id, user)
    return True

def activate_plan(user_id: int, plan_name: str) -> bool:
    """Активировать тариф для пользователя"""
    plan_info = get_plan_info(plan_name)
    if not plan_info:
        log.error(f"Unknown plan: {plan_name}")
        return False
    
    # Получаем данные пользователя
    user = db.get_user(user_id)
    if not user:
        log.error(f"User {user_id} not found")
        return False
    
    # Проверяем, не истек ли текущий тариф
    current_plan = user.get("plan", "lite")
    plan_expiry = user.get("plan_expiry")
    
    # Если тариф продлевается до окончания, добавляем 30 дней
    if current_plan == plan_name and plan_expiry:
        try:
            expiry_date = datetime.fromisoformat(str(plan_expiry).replace('Z', '+00:00'))
            if expiry_date > datetime.now():
                # Продлеваем существующий тариф
                db.activate_plan(user_id, plan_name)
                log.info(f"Extended plan {plan_name} for user {user_id}")
            else:
                # Тариф истек, активируем новый
                db.activate_plan(user_id, plan_name)
                log.info(f"Activated new plan {plan_name} for user {user_id}")
        except Exception as e:
            log.error(f"Error parsing plan expiry: {e}")
            db.activate_plan(user_id, plan_name)
    else:
        # Активируем новый тариф
        db.activate_plan(user_id, plan_name)
        log.info(f"Activated plan {plan_name} for user {user_id}")
    
    # Начисляем монетки по тарифу
    user = db.get_user(user_id)  # Обновляем данные
    if user:
        before_value = user.get("coins", 0)
        user["coins"] = before_value + plan_info["coins"]
        after_value = user.get("coins", 0)
        
        db.save_user(user_id, user)
        
        # Логируем активацию тарифа
        db.add_transaction(
            user_id=user_id,
            operation_type="plan_activation",
            coins_spent=0,
            used_bonus=False,
            before_value=before_value,
            after_value=after_value,
            delta=plan_info["coins"],
            reason=f"plan_{plan_name}_activation",
            metadata={"plan": plan_name, "coins": plan_info["coins"]}
        )
        
        log.info(f"Granted {plan_info['coins']} coins for plan {plan_name}")
        return True
    
    return False

def check_and_reset_expired_plans() -> List[int]:
    """Проверить и сбросить истекшие тарифы"""
    expired_users = db.check_expired_plans()
    reset_users = []
    
    for user_id in expired_users:
        if db.reset_expired_plan(user_id):
            reset_users.append(user_id)
            log.info(f"Reset expired plan for user {user_id}")
    
    return reset_users

def get_user_status(user: Dict[str, Any]) -> Dict[str, Any]:
    """Получить статус пользователя для отображения"""
    plan_info = get_plan_info(user.get("plan", "lite"))
    
    status = {
        "coins": user.get("coins", 0),
        "video_bonus": user.get("video_bonus", 0),
        "photo_bonus": user.get("photo_bonus", 0),
        "tryon_bonus": user.get("tryon_bonus", 0),
        "admin_coins": user.get("admin_coins", 0),
        "plan": user.get("plan", "lite"),
        "plan_name": plan_info["name"] if plan_info else "Лайт",
        "plan_expiry": user.get("plan_expiry"),
        "videos_allowed": user.get("videos_allowed", 0),
        "photos_allowed": user.get("photos_allowed", 0),
        "welcome_granted": user.get("welcome_granted", False)
    }
    
    return status

def format_user_status(user: Dict[str, Any]) -> str:
    """Форматировать статус пользователя для отображения"""
    status = get_user_status(user)
    
    # Проверяем, истек ли тариф
    plan_expired = False
    if status["plan_expiry"] and status["plan"] != "lite":
        try:
            expiry_date = datetime.fromisoformat(str(status["plan_expiry"]).replace('Z', '+00:00'))
            plan_expired = expiry_date < datetime.now()
        except:
            pass
    
    text = f"💰 <b>Ваш профиль</b>\n\n"
    
    # Монетки (основной баланс)
    text += f"💎 <b>Монетки:</b> {status['coins']}\n"
    
    # Тариф
    if plan_expired:
        text += f"\n📋 <b>Тариф:</b> {status['plan_name']} (истек)\n"
    else:
        text += f"\n📋 <b>Тариф:</b> {status['plan_name']}\n"
        if status["plan_expiry"]:
            try:
                expiry_date = datetime.fromisoformat(str(status["plan_expiry"]).replace('Z', '+00:00'))
                text += f"⏰ Действует до: {expiry_date.strftime('%d.%m.%Y %H:%M')}\n"
            except:
                pass
    
    # Стоимость операций
    text += f"\n🎯 <b>Стоимость операций:</b>\n"
    text += f"🎬 Видео: 10 монеток\n"
    text += f"📸 Фото: 1 монетка\n"
    text += f"👗 Примерки: 1 монетка\n"
    
    # Админские монеты (только для админа)
    if status["admin_coins"] > 0:
        text += f"\n👑 <b>Админские монеты:</b> {status['admin_coins']}\n"
    
    return text

def format_plans_list() -> str:
    """Форматировать список тарифов для отображения"""
    text = "📋 <b>Доступные тарифы</b>\n\n"
    
    for plan_key, plan_info in PLANS.items():
        emoji = "✨" if plan_key == "lite" else "⭐" if plan_key == "std" else "💎"
        recommended = " ⭐ РЕКОМЕНДУЕМ" if plan_info.get("recommended") else ""
        
        text += f"{emoji} <b>{plan_info['name']}</b> — {plan_info['price_rub']:,} ₽{recommended}\n"
        text += f"{plan_info['description']}\n"
        text += f"💎 {plan_info['coins']} монеток\n\n"
    
    text += "💡 <i>Тариф действует 30 дней с момента покупки</i>\n"
    text += "🔄 <i>При продлении до окончания добавляется +30 дней</i>\n"
    text += "💰 <i>Подписки выгоднее разовых покупок!</i>"
    
    return text
