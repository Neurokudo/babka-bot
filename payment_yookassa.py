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

def create_payment_link(user_id: int, amount: int, description: str = "", plan: str = None, metadata: dict = None) -> Dict[str, Any]:
    """
    Создать ссылку на оплату (обратная совместимость)
    Теперь использует реальный YooKassa API
    """
    try:
        # Определяем тип платежа по описанию и параметрам
        if "монет" in description.lower() or "topup" in description.lower() or (metadata and metadata.get("type") == "topup"):
            # Пополнение монет
            coins = amount  # В старом API amount был количеством монет
            price_rub = amount * 0.1  # Примерная цена 10 копеек за монету
            payment_url, payment_id = create_topup_payment(user_id, coins, price_rub)
        else:
            # Покупка тарифа
            # Определяем план из параметров или metadata
            if plan:
                target_plan = plan
            elif metadata and metadata.get("plan"):
                target_plan = metadata.get("plan")
            else:
                # Пытаемся определить план из описания
                if "pro" in description.lower():
                    target_plan = "pro"
                elif "standard" in description.lower():
                    target_plan = "standard"
                elif "lite" in description.lower() or "лайт" in description.lower():
                    target_plan = "lite"
                elif "start" in description.lower() or "старт" in description.lower():
                    target_plan = "start"
                else:
                    target_plan = "lite"  # По умолчанию
            
            # Получаем информацию о тарифе
            from app.services.pricing import get_tariff_by_name
            plan_info = get_tariff_by_name(target_plan)
            
            if plan_info:
                coins = plan_info["coins"]
                price_rub = plan_info["price_rub"]
            else:
                # Fallback значения
                coins = amount
                price_rub = amount * 0.1
            
            payment_url, payment_id = create_payment(user_id, target_plan, price_rub, coins)
        
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
