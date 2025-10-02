"""
Веб-сервер для обработки webhook'ов от YooKassa
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from flask import Flask, request, jsonify
from telegram.ext import Application
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from payment_yookassa import verify_webhook_signature, process_payment_webhook
from main import handle_payment_webhook

log = logging.getLogger("webhook-server")
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Глобальная переменная для Telegram Application
telegram_app = None

def init_telegram_app():
    """Инициализация Telegram Application для отправки сообщений"""
    global telegram_app
    if telegram_app is None:
        bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
        telegram_app = Application.builder().token(bot_token).build()
    return telegram_app

@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    """Обработчик webhook'ов от YooKassa"""
    try:
        # Получаем данные запроса
        payload = request.get_data(as_text=True)
        signature = request.headers.get('X-Yookassa-Signature', '')
        
        log.info(f"Received webhook: signature={signature[:20]}..., payload_length={len(payload)}")
        
        # Проверяем подпись (опционально, можно отключить для тестирования)
        if signature and not verify_webhook_signature(payload, signature):
            log.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 401
        
        # Парсим JSON
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in webhook: {e}")
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Обрабатываем webhook асинхронно
        asyncio.create_task(process_webhook_async(webhook_data))
        
        # Возвращаем успешный ответ YooKassa
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        log.error(f"Error processing webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

async def process_webhook_async(webhook_data):
    """Асинхронная обработка webhook'а"""
    try:
        # Инициализируем Telegram Application
        app = init_telegram_app()
        
        # Создаем контекст (заглушка)
        class MockContext:
            def __init__(self):
                self.bot = app.bot
        
        context = MockContext()
        
        # Обрабатываем платеж
        await handle_payment_webhook(webhook_data, context)
        
    except Exception as e:
        log.error(f"Error in async webhook processing: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({"status": "healthy", "service": "babka-bot-webhook"}), 200

@app.route('/', methods=['GET'])
def root():
    """Корневая страница"""
    return jsonify({
        "service": "Babka Bot Webhook Server",
        "status": "running",
        "endpoints": {
            "/webhook/yookassa": "POST - YooKassa webhook handler",
            "/health": "GET - Health check"
        }
    }), 200

def start_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    import threading
    import subprocess
    import sys
    
    def run_bot():
        try:
            log.info("Starting Telegram bot in background...")
            subprocess.run([sys.executable, "main.py"], check=True)
        except Exception as e:
            log.error(f"Error running Telegram bot: {e}")
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return bot_thread

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Запускаем Telegram бота в фоновом режиме (только если не Railway)
    # Railway лучше использовать отдельные сервисы
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        start_telegram_bot()
    
    log.info(f"Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
