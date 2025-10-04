"""
Webhook handler для обработки платежей YooKassa
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from app.services.yookassa_service import process_payment_webhook, process_successful_payment

log = logging.getLogger("webhook_handler")

app = Flask(__name__)

@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    """
    Обработчик webhook'ов от YooKassa
    """
    try:
        # Получаем данные webhook
        webhook_data = request.get_json()
        
        if not webhook_data:
            log.warning("Empty webhook data received")
            return jsonify({"status": "error", "message": "Empty data"}), 400
        
        log.info(f"Received webhook: {webhook_data.get('event', 'unknown')}")
        
        # Обрабатываем webhook
        payment_data = process_payment_webhook(webhook_data)
        
        if not payment_data:
            log.info("Webhook ignored or not supported")
            return jsonify({"status": "ignored"}), 200
        
        event_type = payment_data.get("event")
        payment_id = payment_data.get("payment_id")
        user_id = payment_data.get("user_id")
        
        log.info(f"Processing webhook: event={event_type}, payment_id={payment_id}, user_id={user_id}")
        
        # Обрабатываем только успешные платежи
        if event_type == "payment.succeeded":
            if process_successful_payment(payment_data):
                log.info(f"Successfully processed payment {payment_id} for user {user_id}")
                
                # Здесь можно добавить уведомление пользователю через Telegram Bot API
                # или через очередь сообщений
                
                return jsonify({
                    "status": "success",
                    "message": f"Payment {payment_id} processed successfully"
                }), 200
            else:
                log.error(f"Failed to process payment {payment_id} for user {user_id}")
                return jsonify({
                    "status": "error",
                    "message": f"Failed to process payment {payment_id}"
                }), 500
        
        # Для других событий просто подтверждаем получение
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        log.error(f"Error processing webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
