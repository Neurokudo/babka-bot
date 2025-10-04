"""
Сервер для обработки webhook'ов от Telegram и YooKassa
"""

import os
import logging
from flask import Flask, request, jsonify
from app.web.telegram_web import create_telegram_web_app
from app.services.yookassa_service import process_payment_webhook, process_successful_payment

# Настройка логирования
log = logging.getLogger("babka-bot")

def create_combined_webhook_app():
    """
    Создает объединенное Flask приложение для обработки webhook'ов
    от Telegram и YooKassa
    """
    # Создаем основное Flask приложение
    app = Flask(__name__)
    
    # Получаем токен бота
    bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN not found in environment variables")
    
    # Регистрируем маршруты Telegram webhook напрямую
    @app.route(f'/webhook/{bot_token}', methods=['POST'])
    def telegram_webhook():
        """
        Обработчик webhook'ов от Telegram
        """
        try:
            # Получаем данные webhook
            webhook_data = request.get_json()
            
            if not webhook_data:
                log.warning("Empty webhook data received from Telegram")
                return jsonify({"status": "error", "message": "Empty data"}), 400
            
            log.info("WEBHOOK HIT: method=%s path=%s", request.method, request.url.path)
            
            # Создаем объект Update из данных webhook
            from telegram import Update
            from telegram.ext import Application
            
            # Создаем Application для обработки update
            telegram_app = Application.builder().token(bot_token).build()
            
            # Создаем объект Update
            update = Update.de_json(webhook_data, telegram_app.bot)
            
            if update is None:
                log.warning("Failed to parse Telegram update")
                return jsonify({"status": "error", "message": "Invalid update"}), 400
            
            # Обрабатываем update через диспетчер
            telegram_app.process_update(update)
            
            log.info("Telegram update processed successfully")
            return jsonify({"ok": True}), 200
            
        except Exception as e:
            log.error(f"Error processing Telegram webhook: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"ok": True}), 200
    
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "service": "babka-bot-webhook-server",
            "status": "running",
            "bot_token_suffix": bot_token[-6:] if bot_token else "unknown"
        }), 200
    
    # Регистрируем маршруты YooKassa webhook
    @app.route('/webhook/yookassa', methods=['POST'])
    def yookassa_webhook():
        """
        Обработчик webhook'ов от YooKassa
        """
        try:
            # Получаем данные webhook
            webhook_data = request.get_json()
            
            if not webhook_data:
                log.warning("Empty webhook data received from YooKassa")
                return jsonify({"status": "error", "message": "Empty data"}), 400
            
            log.info(f"Received YooKassa webhook: {webhook_data.get('event', 'unknown')}")
            
            # Обрабатываем webhook
            payment_data = process_payment_webhook(webhook_data)
            
            if not payment_data:
                log.info("YooKassa webhook ignored or not supported")
                return jsonify({"status": "ignored"}), 200
            
            event_type = payment_data.get("event")
            payment_id = payment_data.get("payment_id")
            user_id = payment_data.get("user_id")
            
            log.info(f"Processing YooKassa webhook: event={event_type}, payment_id={payment_id}, user_id={user_id}")
            
            # Обрабатываем только успешные платежи
            if event_type == "payment.succeeded":
                if process_successful_payment(payment_data):
                    log.info(f"Successfully processed payment {payment_id} for user {user_id}")
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
            log.error(f"Error processing YooKassa webhook: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    return app

def run_webhook_server():
    """
    Запускает объединенный webhook сервер
    """
    try:
        app = create_combined_webhook_app()
        port = int(os.getenv('PORT', 8080))
        
        log.info("Starting combined webhook server on port %d", port)
        log.info("Telegram webhook URL: /webhook/{BOT_TOKEN}")
        log.info("YooKassa webhook URL: /webhook/yookassa")
        log.info("Health check URL: /health")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        log.error(f"Failed to start webhook server: {e}")
        raise

if __name__ == '__main__':
    run_webhook_server()
