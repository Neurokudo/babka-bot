#!/usr/bin/env python3
"""
Автоматический мониторинг деплоя webhook сервера
"""
import time
import requests
import json
from datetime import datetime

def check_deployment_status():
    """Проверить статус деплоя"""
    url = "https://babka-bot.railway.app"
    
    try:
        # Проверяем health endpoint
        health_response = requests.get(f"{url}/health", timeout=10)
        
        if health_response.status_code == 200:
            try:
                data = health_response.json()
                if data.get("status") == "healthy" and data.get("service") == "babka-bot-webhook":
                    return "deployed", f"✅ Webhook сервер развернут! {data}"
                else:
                    return "partial", f"⚠️  Сервер отвечает, но не webhook: {data}"
            except json.JSONDecodeError:
                # Старая версия возвращает просто "OK"
                if health_response.text.strip() == "OK":
                    return "old_version", "⏳ Пока работает старая версия (только бот)"
                else:
                    return "unknown", f"⚠️  Неожиданный ответ: {health_response.text}"
        else:
            return "error", f"❌ HTTP {health_response.status_code}: {health_response.text}"
            
    except requests.exceptions.RequestException as e:
        return "offline", f"❌ Сервер недоступен: {e}"

def main():
    """Основная функция мониторинга"""
    print("🔍 МОНИТОРИНГ ДЕПЛОЯ WEBHOOK СЕРВЕРА")
    print("=" * 50)
    print("URL: https://babka-bot.railway.app")
    print("Проверяем каждые 30 секунд...")
    print("Нажмите Ctrl+C для остановки")
    print()
    
    start_time = datetime.now()
    check_count = 0
    
    try:
        while True:
            check_count += 1
            current_time = datetime.now()
            elapsed = current_time - start_time
            
            print(f"[{current_time.strftime('%H:%M:%S')}] Проверка #{check_count} (прошло: {elapsed.seconds//60}м {elapsed.seconds%60}с)")
            
            status, message = check_deployment_status()
            print(f"   {message}")
            
            if status == "deployed":
                print("\n🎉 ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!")
                print("=" * 30)
                print("✅ Webhook сервер работает")
                print("🔗 Webhook URL: https://babka-bot.railway.app/webhook/yookassa")
                print()
                print("📋 СЛЕДУЮЩИЕ ШАГИ:")
                print("1. Настройте webhook в YooKassa:")
                print("   - URL: https://babka-bot.railway.app/webhook/yookassa")
                print("   - События: payment.succeeded, payment.canceled")
                print("2. Протестируйте платеж в боте @babkakudo_bot")
                break
            
            elif status == "error" or status == "offline":
                if elapsed.seconds > 600:  # 10 минут
                    print("\n⚠️  ДЕПЛОЙ ЗАНИМАЕТ СЛИШКОМ МНОГО ВРЕМЕНИ")
                    print("Рекомендуется проверить логи Railway")
                    break
            
            print("   ⏳ Ждем 30 секунд...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n👋 Мониторинг остановлен пользователем")
        print("Вы можете проверить статус вручную:")
        print("curl https://babka-bot.railway.app/health")

if __name__ == "__main__":
    main()
