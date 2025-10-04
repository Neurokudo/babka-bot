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
    # Заглушка для тестирования
    return {
        "success": True,
        "event": "payment.succeeded",
        "payment_id": "test_payment_123",
        "user_id": "123456789",
        "amount": 1990,
        "metadata": {
            "plan": "lite",
            "type": "plan"
        }
    }

def process_successful_payment(payment_data: Dict[str, Any]) -> bool:
    """Обработать успешный платеж и создать подписку"""
    try:
        user_id = int(payment_data.get("user_id", 0))
        amount = payment_data.get("amount", 0)
        metadata = payment_data.get("metadata", {})
        payment_id = payment_data.get("payment_id", "")
        
        if metadata.get("type") == "plan":
            # Создаем подписку
            plan = metadata.get("plan", "lite")
            
            # Получаем информацию о тарифе
            from app.services.pricing import get_tariff_by_name
            plan_info = get_tariff_by_name(plan)
            
            if plan_info:
                from app.db import db_subscriptions as db
                db.create_subscription(
                    user_id=user_id,
                    plan=plan,
                    coins=plan_info["coins"],
                    price_rub=plan_info["price_rub"],
                    duration_days=30,
                    payment_id=payment_id
                )
                return True
        
        elif metadata.get("type") == "topup":
            # Пополнение монет
            coins = metadata.get("coins", 0)
            if coins > 0:
                from app.db import db_subscriptions as db
                # Создаем пользователя если его нет
                db.create_or_update_user(user_id)
                # Добавляем монеты (это можно сделать через update_user_balance)
                # Пока что просто возвращаем True
                return True
        
        return False
        
    except Exception as e:
        print(f"Error processing payment: {e}")
        return False
