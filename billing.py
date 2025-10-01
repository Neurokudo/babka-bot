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

def new_job_id():
    """Генерирует уникальный ID задачи"""
    return str(uuid.uuid4())

def today():
    """Возвращает сегодняшнюю дату в формате YYYY-MM-DD"""
    return date.today().strftime("%Y-%m-%d")

def can_spend(user, cost):
    """Проверяет, может ли пользователь потратить указанное количество монет"""
    return user.get("coins", 0) >= cost

def hold_and_start(user, job_type, quality="basic", extra_cost=0):
    """
    Резервирует монеты и создает задачу
    
    Args:
        user: состояние пользователя
        job_type: "video" | "transform"
        quality: "basic" | "premium"
        extra_cost: дополнительные монеты (для сложных операций)
    """
    if job_type == "video":
        cost = COST_VIDEO
    else:  # transform
        cost = COST_TRANSFORM_PREMIUM if quality == "premium" else COST_TRANSFORM
        cost += extra_cost
    
    if not can_spend(user, cost):
        raise ValueError("NO_COINS")
    
    # Списываем монеты
    user["coins"] -= cost
    
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
        "created_at": datetime.now().isoformat()
    }
    
    # Обновляем last_job для совместимости
    user["last_job"] = user["jobs"][job_id]
    
    return job_id

def on_success(user, job_id):
    """Отмечает задачу как успешную"""
    if "jobs" in user and job_id in user["jobs"]:
        user["jobs"][job_id]["status"] = "ok"
        user["jobs"][job_id]["completed_at"] = datetime.now().isoformat()
        
        # Обновляем last_job
        user["last_job"] = user["jobs"][job_id]
        
        # Увеличиваем счетчик видео за день
        if user["jobs"][job_id]["type"] == "video":
            inc_daily_video(user)

def on_error(user, job_id):
    """Возвращает монеты при ошибке"""
    if "jobs" not in user or job_id not in user["jobs"]:
        return
    
    job = user["jobs"][job_id]
    if job["status"] == "pending":
        # Возвращаем монеты
        user["coins"] += job["cost"]
        job["status"] = "error"
        job["error_at"] = datetime.now().isoformat()
        
        # Обновляем last_job
        user["last_job"] = job

def retry(user, job_id):
    """
    Пытается сделать ретрай задачи
    
    Returns:
        bool: True если ретрай разрешен, False если не хватает монет
    """
    if "jobs" not in user or job_id not in user["jobs"]:
        return False
    
    job = user["jobs"][job_id]
    
    # Проверяем количество использованных ретраев
    if job["retry_used"] < FREE_RETRY_PER_JOB:
        # Бесплатный ретрай
        job["retry_used"] += 1
        return True
    
    # Платный ретрай
    cost = job["cost"]
    if can_spend(user, cost):
        user["coins"] -= cost
        job["retry_used"] += 1
        return True
    
    return False

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
