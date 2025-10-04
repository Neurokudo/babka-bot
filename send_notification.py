#!/usr/bin/env python3
"""
Скрипт для отправки уведомления пользователю о исправленной подписке
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def send_notification():
    """Отправляем уведомление пользователю"""
    user_id = 5015100177
    
    # Попробуем получить токен из переменных окружения
    bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
    
    if not bot_token:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        print("💡 Попробуйте запустить бот и проверить профиль через команду /start")
        return False
    
    success_message = (
        '🎉 <b>Поздравляем! Ваша подписка исправлена!</b>\n\n'
        '📋 Тариф: Про\n'
        '💰 Получено: 440 монеток\n'
        '⏰ Действует: до 03.11.2025 21:44\n\n'
        '🚀 Теперь вы можете пользоваться всеми функциями бота!\n\n'
        '💡 Подписка будет продлена автоматически, пока вы её не отмените.\n\n'
        '✅ Проблема решена! Извините за неудобства.'
    )
    
    try:
        import requests
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': user_id,
            'text': success_message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print('✅ Уведомление отправлено успешно!')
            return True
        else:
            print(f'❌ Ошибка отправки: {response.status_code} - {response.text}')
            return False
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        return False

if __name__ == "__main__":
    send_notification()
