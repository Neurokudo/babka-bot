"""
Модуль для работы с платежами YooKassa
Импортирует функции из нового сервиса для обратной совместимости
"""

from typing import Dict, Any
from app.services.yookassa_service import (
    create_payment,
    create_topup_payment,
    process_payment_webhook,
    process_successful_payment,
    check_payment_status
)

def create_payment_link(user_id: int, amount: int, description: str = "") -> Dict[str, Any]:
    """
    Создать ссылку на оплату (обратная совместимость)
    Теперь использует реальный YooKassa API
    """
    try:
        # Определяем тип платежа по описанию
        if "монет" in description.lower() or "topup" in description.lower():
            # Пополнение монет
            coins = amount  # В старом API amount был количеством монет
            price_rub = amount * 0.1  # Примерная цена 10 копеек за монету
            payment_url, payment_id = create_topup_payment(user_id, coins, price_rub)
        else:
            # Покупка тарифа
            plan = "lite"  # По умолчанию
            coins = amount
            price_rub = amount * 0.1
            payment_url, payment_id = create_payment(user_id, plan, price_rub, coins)
        
        return {
            "success": True,
            "payment_url": payment_url,
            "payment_id": payment_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "payment_url": None,
            "payment_id": None
        }
