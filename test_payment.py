#!/usr/bin/env python3
"""
Скрипт для тестирования платежей
"""
import asyncio
import json
from main import handle_payment_webhook

# Тестовые данные webhook'а от ЮKassa
test_webhook_data = {
    "type": "notification",
    "event": "payment.succeeded",
    "object": {
        "id": "test_payment_123",
        "status": "succeeded",
        "amount": {
            "value": "1990.00",
            "currency": "RUB"
        },
        "metadata": {
            "user_id": 123456789,  # Замените на ваш user_id
            "plan": "lite",
            "type": "plan"
        }
    }
}

async def test_payment():
    """Тестируем обработку платежа"""
    print("Тестируем обработку платежа...")
    
    # Создаем mock context
    class MockContext:
        async def send_message(self, chat_id, text, reply_markup=None):
            print(f"Отправляем сообщение пользователю {chat_id}:")
            print(f"Текст: {text}")
            if reply_markup:
                print(f"Клавиатура: {reply_markup}")
    
    context = MockContext()
    
    try:
        await handle_payment_webhook(test_webhook_data, context)
        print("✅ Платеж обработан успешно!")
    except Exception as e:
        print(f"❌ Ошибка обработки платежа: {e}")

if __name__ == "__main__":
    asyncio.run(test_payment())
