#!/usr/bin/env python3
"""
Скрипт для локального запуска бота и webhook сервера
"""
import os
import sys
import time
import signal
import subprocess
from pathlib import Path

def start_processes():
    """Запуск бота и webhook сервера в отдельных процессах"""
    processes = []
    
    try:
        # Запускаем webhook сервер
        print("🌐 Запускаем webhook сервер...")
        webhook_process = subprocess.Popen([
            sys.executable, "webhook_server.py"
        ], cwd=Path(__file__).parent)
        processes.append(("webhook_server", webhook_process))
        
        # Даем серверу время запуститься
        time.sleep(2)
        
        # Запускаем бота
        print("🤖 Запускаем Telegram бота...")
        bot_process = subprocess.Popen([
            sys.executable, "main.py"
        ], cwd=Path(__file__).parent)
        processes.append(("main_bot", bot_process))
        
        print("✅ Оба процесса запущены!")
        print("📡 Webhook сервер: http://localhost:8000")
        print("🤖 Telegram бот работает в polling режиме")
        print("\nДля остановки нажмите Ctrl+C")
        
        # Ждем сигнала завершения
        def signal_handler(signum, frame):
            print("\n🛑 Получен сигнал завершения...")
            for name, process in processes:
                print(f"⏹️  Останавливаем {name}...")
                process.terminate()
            
            # Ждем завершения процессов
            for name, process in processes:
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} остановлен")
                except subprocess.TimeoutExpired:
                    print(f"⚠️  Принудительно завершаем {name}...")
                    process.kill()
            
            print("👋 Все процессы остановлены")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Мониторим процессы
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    print(f"❌ Процесс {name} завершился с кодом {process.returncode}")
                    return
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Получено прерывание...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        # Завершаем все процессы
        for name, process in processes:
            if process.poll() is None:
                print(f"⏹️  Останавливаем {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

if __name__ == "__main__":
    start_processes()
