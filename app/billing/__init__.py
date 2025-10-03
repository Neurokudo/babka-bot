# -*- coding: utf-8 -*-
"""
Billing system - coins, plans, payments
"""

# Старые импорты удалены - используем новую систему app.services.wallet

# Импорты из plans.py
from .plans import (
    activate_plan,
    check_subscription,
    check_and_reset_expired_plans,
    get_user_plan_info,
    is_plan_active,
    get_plan_expiry_text,
    give_welcome_bonus
)

# Функции для совместимости с новой системой
def can_spend(user_data, cost):
    """Проверка возможности трат"""
    from app.services.wallet import get_balance
    user_id = user_data.get('user_id', 0)
    return get_balance(user_id) >= cost

def hold_and_start(user_data, operation_type, quality=None):
    """Создание задачи с проверкой баланса"""
    from app.services.wallet import get_balance, charge_feature
    from app.services.pricing import feature_cost_coins
    import uuid
    
    user_id = user_data.get('user_id', 0)
    
    # Определяем feature_key для операции
    feature_key = None
    if operation_type == "video":
        feature_key = "video_8s_audio"  # по умолчанию с аудио
    elif operation_type == "transform":
        feature_key = "image_basic"
    elif operation_type == "tryon":
        feature_key = "virtual_tryon"
    elif operation_type == "json":
        feature_key = "video_8s_audio"
    
    if not feature_key:
        raise ValueError(f"Unknown operation type: {operation_type}")
    
    cost = feature_cost_coins(feature_key)
    
    # Проверяем баланс и списываем монеты
    if not charge_feature(user_id, feature_key):
        raise ValueError("Insufficient funds")
    
    # Создаем задачу
    job_id = str(uuid.uuid4())
    user_data['current_job_id'] = job_id
    user_data['jobs'] = user_data.get('jobs', {})
    user_data['jobs'][job_id] = {
        'type': operation_type,
        'quality': quality,
        'status': 'pending',
        'coin_cost': cost
    }
    
    # Обновляем баланс в user_data
    user_data['coins'] = get_balance(user_id)
    
    return job_id

def on_success(user_data, job_id):
    """Обработка успешного завершения задачи"""
    if job_id in user_data.get('jobs', {}):
        user_data['jobs'][job_id]['status'] = 'completed'

def on_error(user_data, job_id, reason=None):
    """Обработка ошибки задачи"""
    if job_id in user_data.get('jobs', {}):
        user_data['jobs'][job_id]['status'] = 'failed'
        user_data['jobs'][job_id]['error'] = reason

def retry(user_data, job_id):
    """Повтор задачи"""
    if job_id in user_data.get('jobs', {}):
        job = user_data['jobs'][job_id]
        operation_type = job.get('type')
        quality = job.get('quality')
        
        try:
            new_job_id = hold_and_start(user_data, operation_type, quality)
            return True
        except ValueError:
            return False
    return False

def check_low_coins(user_data):
    """Проверка низкого баланса"""
    from app.services.wallet import get_balance
    user_id = user_data.get('user_id', 0)
    balance = get_balance(user_id)
    return balance < 15  # LOW_COINS_THRESHOLD

def get_retry_cost(user_data, job_id):
    """Получение стоимости повтора"""
    if job_id in user_data.get('jobs', {}):
        return user_data['jobs'][job_id].get('coin_cost', 0)
    return 0

def can_retry(user_data, job_id):
    """Проверка возможности повтора"""
    cost = get_retry_cost(user_data, job_id)
    return can_spend(user_data, cost)

def can_generate_video(user_data):
    """Проверка возможности генерации видео"""
    from app.services.wallet import get_balance
    from app.services.pricing import feature_cost_coins
    user_id = user_data.get('user_id', 0)
    balance = get_balance(user_id)
    cost = feature_cost_coins("video_8s_audio")
    return balance >= cost

def can_generate_photo(user_data, cost):
    """Проверка возможности генерации фото"""
    return can_spend(user_data, cost)

def can_generate_tryon(user_data):
    """Проверка возможности генерации примерочной"""
    from app.services.wallet import get_balance
    from app.services.pricing import feature_cost_coins
    user_id = user_data.get('user_id', 0)
    balance = get_balance(user_id)
    cost = feature_cost_coins("virtual_tryon")
    return balance >= cost

def can_generate_json(user_data):
    """Проверка возможности генерации JSON"""
    from app.services.wallet import get_balance
    from app.services.pricing import feature_cost_coins
    user_id = user_data.get('user_id', 0)
    balance = get_balance(user_id)
    cost = feature_cost_coins("video_8s_audio")
    return balance >= cost

def apply_top_up(user_data, coins):
    """Применение пополнения"""
    from app.services.wallet import add_coins
    user_id = user_data.get('user_id', 0)
    add_coins(user_id, coins, "topup_purchase")
    user_data['coins'] = user_data.get('coins', 0) + coins
    return True

def get_cost_for_operation(operation_type, quality=None):
    """Получение стоимости операции"""
    from app.services.pricing import feature_cost_coins
    
    if operation_type == "video":
        return feature_cost_coins("video_8s_audio")
    elif operation_type == "transform":
        return feature_cost_coins("image_basic")
    elif operation_type == "tryon":
        return feature_cost_coins("virtual_tryon")
    elif operation_type == "json":
        return feature_cost_coins("video_8s_audio")
    return 0