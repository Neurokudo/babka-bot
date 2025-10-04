"""
Telegram webhook handler для обработки обновлений от Telegram Bot API
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application

log = logging.getLogger("babka-bot")

def create_telegram_web_app(bot_token: str, application: Application) -> Flask:
    """
    Создает Flask приложение для обработки Telegram webhook'ов
    
    Args:
        bot_token: Токен бота Telegram
        application: Экземпляр Application из python-telegram-bot
    
    Returns:
        Flask приложение с настроенными маршрутами
    """
    app = Flask(__name__)
    
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
            update = Update.de_json(webhook_data, application.bot)
            
            if update is None:
                log.warning("Failed to parse Telegram update")
                return jsonify({"status": "error", "message": "Invalid update"}), 400
            
            # Обрабатываем update через диспетчер
            # В python-telegram-bot v20+ используется другой подход
            # Нужно использовать application.process_update()
            application.process_update(update)
            
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
        """Проверка здоровья сервиса"""
        return jsonify({"ok": True}), 200
    
    @app.route('/', methods=['GET'])
    def root():
        """Корневой маршрут для проверки доступности"""
        return jsonify({
            "service": "babka-bot-telegram-webhook",
            "status": "running",
            "bot_token_suffix": bot_token[-6:] if bot_token else "unknown"
        }), 200
    
    return app

def run_telegram_webhook_server(app: Flask, port: int = None):
    """
    Запускает Flask сервер для обработки Telegram webhook'ов
    
    Args:
        app: Flask приложение
        port: Порт для запуска (по умолчанию из переменной окружения PORT)
    """
    if port is None:
        port = int(os.getenv('PORT', 8080))
    
    log.info("Starting Telegram webhook server on port %d", port)
    app.run(host='0.0.0.0', port=port, debug=False)
