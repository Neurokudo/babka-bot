"""
Заглушка для payment_yookassa - модуль для работы с платежами
"""

from typing import Dict, Any

def create_payment_link(user_id: int, amount: int, description: str = "") -> Dict[str, Any]:
    """Создать ссылку на оплату"""
    return {
        "success": True,
        "payment_url": f"https://example.com/pay/{user_id}/{amount}",
        "payment_id": f"test_payment_{user_id}_{amount}"
    }

def process_payment_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Обработать webhook от платежной системы"""
    return {
        "success": True,
        "status": "succeeded"
    }
