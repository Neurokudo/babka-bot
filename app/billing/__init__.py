# -*- coding: utf-8 -*-
"""
Billing system - coins, plans, payments
"""

# Импорты из подмодулей
from .coins import (
    atomic_spend_coins,
    add_coins,
    get_balance,
    can_afford,
    add_admin_coins,
    get_admin_balance,
    update_transaction_status,
    refund_coins,
)

from .plans import (
    check_subscription,
    activate_plan,
    check_and_reset_expired_plans,
    get_user_plan_info,
    is_plan_active,
    get_plan_expiry_text,
    give_welcome_bonus,
)

from .payments import (
    create_payment_record,
    update_payment_status,
    process_payment_success,
    process_payment_failure,
    is_payment_processed,
    get_payment_by_idempotent_key,
    validate_webhook_signature,
    process_yookassa_webhook,
)

# Заглушки для старых функций (временно)
def can_spend(user_data, cost):
    """Проверка возможности трат"""
    return user_data.get('coins', 0) >= cost

def hold_and_start(user_data, operation_type, quality=None):
    """Заглушка для hold_and_start"""
    import uuid
    job_id = str(uuid.uuid4())
    user_data['current_job_id'] = job_id
    user_data['jobs'] = user_data.get('jobs', {})
    user_data['jobs'][job_id] = {
        'type': operation_type,
        'quality': quality,
        'status': 'pending',
        'coin_cost': get_cost_for_operation(operation_type, quality)
    }
    return job_id

def on_success(user_data, job_id):
    """Заглушка для on_success"""
    if job_id in user_data.get('jobs', {}):
        user_data['jobs'][job_id]['status'] = 'completed'

def on_error(user_data, job_id, reason=None):
    """Заглушка для on_error"""
    if job_id in user_data.get('jobs', {}):
        user_data['jobs'][job_id]['status'] = 'failed'
        user_data['jobs'][job_id]['error'] = reason

def retry(user_data, job_id):
    """Заглушка для retry"""
    if job_id in user_data.get('jobs', {}):
        job = user_data['jobs'][job_id]
        cost = job.get('coin_cost', 0)
        if can_spend(user_data, cost):
            atomic_spend_coins(user_data['user_id'], cost, f"retry_{job['type']}")
            user_data['coins'] = user_data.get('coins', 0) - cost
            return True
    return False

def check_low_coins(user_data):
    """Проверка низкого баланса"""
    from .config import LOW_COINS_THRESHOLD
    return user_data.get('coins', 0) < LOW_COINS_THRESHOLD

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
    from .config import COST_VIDEO
    return can_spend(user_data, COST_VIDEO)

def can_generate_photo(user_data, cost):
    """Проверка возможности генерации фото"""
    return can_spend(user_data, cost)

def can_generate_tryon(user_data):
    """Проверка возможности генерации примерочной"""
    from .config import COST_TRYON
    return can_spend(user_data, COST_TRYON)

def can_generate_json(user_data):
    """Проверка возможности генерации JSON"""
    from .config import COST_VIDEO
    return can_spend(user_data, COST_VIDEO)

def apply_top_up(user_data, coins):
    """Применение пополнения"""
    user_data['coins'] = user_data.get('coins', 0) + coins
    return True

def get_cost_for_operation(operation_type, quality=None):
    """Получение стоимости операции"""
    from .config import COST_VIDEO, COST_TRANSFORM, COST_TRANSFORM_PREMIUM, COST_TRYON
    
    if operation_type == "video":
        return COST_VIDEO
    elif operation_type == "transform":
        return COST_TRANSFORM_PREMIUM if quality == "premium" else COST_TRANSFORM
    elif operation_type == "tryon":
        return COST_TRYON
    elif operation_type == "json":
        return COST_VIDEO
    return 0