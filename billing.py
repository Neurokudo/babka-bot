# -*- coding: utf-8 -*-
"""
Модуль биллинга и управления монетами
"""

import uuid
from datetime import datetime, date
from config import (
    COST_VIDEO, COST_TRANSFORM, COST_TRANSFORM_PREMIUM, 
    FREE_RETRY_PER_JOB, DAILY_CAP_VIDEOS, LOW_COINS_THRESHOLD
)
from database import db

def new_job_id():
    """Генерирует уникальный ID задачи"""
    return str(uuid.uuid4())

def today():
    """Возвращает сегодняшнюю дату в формате YYYY-MM-DD"""
    return date.today().strftime("%Y-%m-%d")

def can_spend(user, cost):
    """Проверяет, может ли пользователь потратить указанное количество монет"""
    return user.get("coins", 0) >= cost

def has_video_bonus(user):
    """Проверяет, есть ли у пользователя бонусные видео"""
    return user.get("video_bonus", 0) > 0

def has_photo_bonus(user):
    """Проверяет, есть ли у пользователя бонусные фото"""
    return user.get("photo_bonus", 0) > 0

def can_generate_video(user):
    """Проверяет, может ли пользователь сгенерировать видео (бонус или монеты)"""
    # Используем новую систему тарифов
    from subscription_system import can_generate_video_with_plan
    return can_generate_video_with_plan(user)

def can_generate_photo(user, cost=None):
    """Проверяет, может ли пользователь сгенерировать фото (бонус или монеты)"""
    # Используем новую систему тарифов
    from subscription_system import can_generate_photo_with_plan
    return can_generate_photo_with_plan(user, cost)

def hold_and_start(user, job_type, quality="basic", extra_cost=0):
    """
    Резервирует ресурсы (бонусы или монеты) и создает задачу
    
    Args:
        user: состояние пользователя
        job_type: "video" | "transform"
        quality: "basic" | "premium"
        extra_cost: дополнительные монеты (для сложных операций)
    """
    user_id = user.get("user_id")
    
    # Используем новую систему списания ресурсов
    from subscription_system import spend_video_resource, spend_photo_resource
    
    if job_type == "video":
        if not spend_video_resource(user):
            raise ValueError("NO_COINS")
        cost = 0  # Ресурс уже списан в spend_video_resource
        bonus_type = "video_bonus" if user.get("video_bonus", 0) > 0 else "plan_limit" if user.get("videos_allowed", 0) > 0 else None
    else:  # transform
        cost = COST_TRANSFORM_PREMIUM if quality == "premium" else COST_TRANSFORM
        cost += extra_cost
        
        if not spend_photo_resource(user, cost):
            raise ValueError("NO_COINS")
        cost = 0  # Ресурс уже списан в spend_photo_resource
        bonus_type = "photo_bonus" if user.get("photo_bonus", 0) > 0 else "plan_limit" if user.get("photos_allowed", 0) > 0 else None
    
    # Создаем задачу
    job_id = new_job_id()
    if "jobs" not in user:
        user["jobs"] = {}
    
    user["jobs"][job_id] = {
        "type": job_type,
        "cost": cost,
        "retry_used": 0,
        "status": "pending",
        "quality": quality,
        "created_at": datetime.now().isoformat(),
        "used_bonus": cost == 0,  # Отмечаем, что использовали бонус
        "transaction_id": None  # Транзакция уже создана в spend_*_resource
    }
    
    # Обновляем last_job для совместимости
    user["last_job"] = user["jobs"][job_id]
    
    return job_id

def on_success(user, job_id):
    """Отмечает задачу как успешную"""
    user_id = user.get("user_id")
    
    if "jobs" in user and job_id in user["jobs"]:
        user["jobs"][job_id]["status"] = "ok"
        user["jobs"][job_id]["completed_at"] = datetime.now().isoformat()
        
        # Обновляем статус транзакции в базе данных
        if user_id and user["jobs"][job_id].get("transaction_id"):
            db.update_transaction_status(
                user["jobs"][job_id]["transaction_id"], 
                "completed"
            )
        
        # Сохраняем изменения пользователя
        if user_id:
            db.save_user(user_id, user)
        
        # Обновляем last_job
        user["last_job"] = user["jobs"][job_id]
        
        # Увеличиваем счетчик видео за день
        if user["jobs"][job_id]["type"] == "video":
            inc_daily_video(user)

def on_error(user, job_id):
    """Возвращает ресурсы (бонусы или монеты) при ошибке"""
    user_id = user.get("user_id")
    
    if "jobs" not in user or job_id not in user["jobs"]:
        return
    
    job = user["jobs"][job_id]
    if job["status"] == "pending":
        if job.get("used_bonus", False):
            if job["type"] == "video":
                user["video_bonus"] += 1
            else:  # transform
                user["photo_bonus"] += 1
        else:
            # Возвращаем монеты
            user["coins"] += job["cost"]
        
        job["status"] = "error"
        job["error_at"] = datetime.now().isoformat()
        
        # Обновляем статус транзакции в базе данных
        if user_id and job.get("transaction_id"):
            db.update_transaction_status(job["transaction_id"], "error")
        
        # Сохраняем изменения пользователя
        if user_id:
            db.save_user(user_id, user)
        
        # Обновляем last_job
        user["last_job"] = job

def retry(user, job_id):
    """
    Пытается сделать ретрай задачи
    
    Returns:
        bool: True если ретрай разрешен, False если не хватает ресурсов
    """
    user_id = user.get("user_id")
    
    if "jobs" not in user or job_id not in user["jobs"]:
        return False
    
    job = user["jobs"][job_id]
    
    # Проверяем количество использованных ретраев
    if job["retry_used"] < FREE_RETRY_PER_JOB:
        # Бесплатный ретрай
        job["retry_used"] += 1
        
        # Сохраняем изменения
        if user_id:
            db.save_user(user_id, user)
        
        return True
    
    # Платный ретрай - используем бонусы или монеты
    if job["type"] == "video":
        if has_video_bonus(user):
            user["video_bonus"] -= 1
            job["retry_used"] += 1
            bonus_type = "video_bonus"
        elif can_spend(user, job["cost"]):
            user["coins"] -= job["cost"]
            job["retry_used"] += 1
            bonus_type = None
        else:
            return False
    else:  # transform
        if has_photo_bonus(user):
            user["photo_bonus"] -= 1
            job["retry_used"] += 1
            bonus_type = "photo_bonus"
        elif can_spend(user, job["cost"]):
            user["coins"] -= job["cost"]
            job["retry_used"] += 1
            bonus_type = None
        else:
            return False
    
    # Создаем новую транзакцию для ретрая
    if user_id:
        db.save_user(user_id, user)
        db.add_transaction(
            user_id=user_id,
            operation_type=f"{job['type']}_retry",
            coins_spent=job["cost"] if bonus_type is None else 0,
            used_bonus=(bonus_type is not None),
            bonus_type=bonus_type,
            quality=job.get("quality", "basic")
        )
    
    return True

def check_daily_cap(user, job_type):
    """
    Проверяет дневной лимит для типа задачи
    
    Args:
        user: состояние пользователя
        job_type: "video" | "transform"
    
    Returns:
        bool: True если лимит не превышен
    """
    if job_type != "video":
        return True
    
    # Инициализируем дневные данные если нужно
    if "daily" not in user:
        user["daily"] = {"date": today(), "videos": 0}
    
    # Сбрасываем счетчик если новый день
    if user["daily"]["date"] != today():
        user["daily"] = {"date": today(), "videos": 0}
    
    # Получаем план пользователя
    plan = user.get("plan", "light")
    max_videos = DAILY_CAP_VIDEOS.get(plan, 3)
    
    return user["daily"]["videos"] < max_videos

def inc_daily_video(user):
    """Увеличивает счетчик видео за день"""
    if "daily" not in user:
        user["daily"] = {"date": today(), "videos": 0}
    
    if user["daily"]["date"] != today():
        user["daily"] = {"date": today(), "videos": 0}
    
    user["daily"]["videos"] += 1

def get_daily_videos_left(user):
    """Возвращает количество оставшихся видео за день"""
    if "daily" not in user:
        return DAILY_CAP_VIDEOS.get(user.get("plan", "light"), 3)
    
    if user["daily"]["date"] != today():
        return DAILY_CAP_VIDEOS.get(user.get("plan", "light"), 3)
    
    plan = user.get("plan", "light")
    max_videos = DAILY_CAP_VIDEOS.get(plan, 3)
    return max_videos - user["daily"]["videos"]

def check_low_coins(user):
    """Проверяет, нужно ли показать уведомление о низком балансе"""
    return user.get("coins", 0) < LOW_COINS_THRESHOLD

def get_retry_cost(user, job_id):
    """Возвращает стоимость ретрая для задачи"""
    if "jobs" not in user or job_id not in user["jobs"]:
        return 0
    
    job = user["jobs"][job_id]
    
    if job["retry_used"] < FREE_RETRY_PER_JOB:
        return 0  # Бесплатный ретрай
    
    return job["cost"]  # Платный ретрай

def can_retry(user, job_id):
    """Проверяет, может ли пользователь сделать ретрай"""
    if "jobs" not in user or job_id not in user["jobs"]:
        return False
    
    job = user["jobs"][job_id]
    
    # Бесплатный ретрай
    if job["retry_used"] < FREE_RETRY_PER_JOB:
        return True
    
    # Платный ретрай
    return can_spend(user, job["cost"])
