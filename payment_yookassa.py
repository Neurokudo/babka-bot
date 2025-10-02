"""
Модуль для интеграции с ЮKassa
"""
import os
import json
import logging
import hashlib
import hmac
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

log = logging.getLogger("babka-bot")

# Конфигурация ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1147356")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "test_9ABcICTErBa5ps3UNBq8N1zQTKFQgCvnBB6EV89-Wag")
YOOKASSA_BASE_URL = "https://api.yookassa.ru/v3"

class YooKassaError(Exception):
    pass

class YooKassaClient:
    def __init__(self, shop_id: str, secret_key: str):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.base_url = YOOKASSA_BASE_URL
        self.auth = (shop_id, secret_key)
        
    def create_payment(self, amount: float, currency: str = "RUB", 
                      description: str = "", metadata: Dict[str, Any] = None,
                      return_url: str = None) -> Dict[str, Any]:
        """Создать платеж в ЮKassa"""
        try:
            payload = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or "https://t.me/your_bot"
                },
                "description": description,
                "metadata": metadata or {},
                "receipt": {
                    "customer": {
                        "email": "customer@example.com"
                    },
                    "items": [
                        {
                            "description": description,
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{amount:.2f}",
                                "currency": currency
                            },
                            "vat_code": 1,  # НДС не облагается
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                }
            }
            
            # Генерируем уникальный ключ идемпотентности
            idempotence_key = str(uuid.uuid4())
            
            headers = {
                "Content-Type": "application/json",
                "Idempotence-Key": idempotence_key
            }
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                auth=self.auth,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log.error(f"YooKassa API error: {response.status_code} - {response.text}")
                raise YooKassaError(f"API error: {response.status_code}")
                
        except Exception as e:
            log.error(f"Error creating YooKassa payment: {e}")
            raise YooKassaError(str(e))
    
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Получить информацию о платеже"""
        try:
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log.error(f"YooKassa API error: {response.status_code} - {response.text}")
                raise YooKassaError(f"API error: {response.status_code}")
                
        except Exception as e:
            log.error(f"Error getting YooKassa payment: {e}")
            raise YooKassaError(str(e))

# Глобальный клиент (создается лениво, чтобы избежать ошибок во время сборки)
yookassa_client = None

def get_yookassa_client():
    """Получить клиент YooKassa (ленивая инициализация)"""
    global yookassa_client
    if yookassa_client is None:
        yookassa_client = YooKassaClient(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    return yookassa_client

def create_payment_link(user_id: int, amount: float, description: str, 
                       metadata: Dict[str, Any] = None) -> str:
    """Создать ссылку для оплаты"""
    try:
        # Проверяем, что у нас есть настоящие ключи
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            raise YooKassaError("YooKassa credentials not configured")
        
        # Режим разработки - создаем заглушку для тестирования
        if YOOKASSA_SHOP_ID == "1147356" and "test_" in YOOKASSA_SECRET_KEY:
            # Тестовый режим - создаем заглушку
            log.warning(f"Test mode: creating test payment link for user {user_id}, amount {amount}")
            log.warning("⚠️ ВНИМАНИЕ: Используются тестовые ключи YooKassa! Реальные платежи не работают!")
            return f"https://yoomoney.ru/checkout/payments/v2/?orderId=test_{user_id}_{int(amount)}"
        
        payment_metadata = {
            "user_id": str(user_id),
            "telegram_bot": True
        }
        if metadata:
            payment_metadata.update(metadata)
            
        client = get_yookassa_client()
        payment = client.create_payment(
            amount=amount,
            description=description,
            metadata=payment_metadata,
            return_url=f"https://t.me/babka_ai_bot"
        )
        
        # Получаем URL для оплаты
        confirmation = payment.get("confirmation", {})
        payment_url = confirmation.get("confirmation_url")
        
        if not payment_url:
            raise YooKassaError("No payment URL received")
            
        log.info(f"Payment created successfully for user {user_id}, amount {amount}, payment_id: {payment.get('id')}")
        return payment_url
        
    except Exception as e:
        log.error(f"Error creating payment link: {e}")
        # В случае ошибки НЕ возвращаем тестовую ссылку, а показываем ошибку
        raise YooKassaError(f"Не удалось создать платеж: {str(e)}")

def verify_webhook_signature(payload: str, signature: str) -> bool:
    """Проверить подпись webhook'а от ЮKassa"""
    try:
        expected_signature = hmac.new(
            YOOKASSA_SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        log.error(f"Error verifying webhook signature: {e}")
        return False

def process_payment_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Обработать webhook от ЮKassa"""
    try:
        event_type = webhook_data.get("event")
        if event_type != "payment.succeeded":
            return None
            
        payment_object = webhook_data.get("object", {})
        if not payment_object:
            return None
            
        payment_id = payment_object.get("id")
        amount = payment_object.get("amount", {})
        metadata = payment_object.get("metadata", {})
        
        if not payment_id or not amount:
            return None
            
        return {
            "payment_id": payment_id,
            "amount": float(amount.get("value", 0)),
            "currency": amount.get("currency", "RUB"),
            "user_id": metadata.get("user_id"),
            "metadata": metadata,
            "status": payment_object.get("status")
        }
        
    except Exception as e:
        log.error(f"Error processing payment webhook: {e}")
        return None
