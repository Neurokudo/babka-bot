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
        user_states[user_id] = {
            "coins": 100,  # Заглушка для тестирования
            "current_job_id": None,
            "jobs": {},
            "tariff": None,
            "tariff_expires": None
        }
    return user_states[user_id]

def can_spend(user_id: int, feature_key: str) -> bool:
    """Проверить, может ли пользователь потратить монеты на функцию"""
    st = get_user_state(user_id)
    cost = feature_cost_coins(feature_key)
    return st.get("coins", 0) >= cost

def hold_and_start(user_id: int, feature_type: str, quality: str = "basic") -> str:
    """Заблокировать монеты и начать задачу"""
    st = get_user_state(user_id)
    
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
    if st.get("coins", 0) < cost:
        raise ValueError(f"Недостаточно монет. Нужно: {cost}, у вас: {st.get('coins', 0)}")
    
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
    st = get_user_state(user_id)
    coins = st.get("coins", 0)
    return coins < 20  # Считаем низким баланс меньше 20 монет

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
    st = get_user_state(user_id)
    return st.get("coins", 0)

def add_coins(user_id: int, amount: int) -> bool:
    """Добавить монеты пользователю"""
    st = get_user_state(user_id)
    st["coins"] = st.get("coins", 0) + amount
    log.info(f"Added {amount} coins to user {user_id}, new balance: {st['coins']}")
    return True

def spend_coins(user_id: int, amount: int) -> bool:
    """Потратить монеты пользователя"""
    st = get_user_state(user_id)
    if st.get("coins", 0) >= amount:
        st["coins"] -= amount
        log.info(f"Spent {amount} coins from user {user_id}, new balance: {st['coins']}")
        return True
    return False

# Дополнительные функции для совместимости
def can_generate_photo(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать фото"""
    return can_spend(user_id, "transform")

def can_generate_tryon(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать виртуальную примерочную"""
    return can_spend(user_id, "tryon")

def can_generate_json(user_id: int) -> bool:
    """Проверить, может ли пользователь генерировать JSON"""
    return can_spend(user_id, "json")

def activate_plan(user_id: int, plan_name: str) -> bool:
    """Активировать план для пользователя"""
    st = get_user_state(user_id)
    st["tariff"] = plan_name
    st["tariff_expires"] = datetime.now() + timedelta(days=30)
    log.info(f"Activated plan {plan_name} for user {user_id}")
    return True

def apply_top_up(user_id: int, coins: int) -> bool:
    """Применить пополнение монет"""
    return add_coins(user_id, coins)
