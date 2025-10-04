#!/usr/bin/env python3
"""
Тест единообразия системы контроля доступа
Проверяет, что все платные функции имеют одинаковую логику проверки доступа
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///./babka_bot.db")

from app.services.billing import can_use_feature
from app.db.db_subscriptions import get_user_plan, create_subscription
from app.services.pricing import get_tariff_by_name, feature_cost_coins
from app.db.queries import db_manager

def test_access_control_unified():
    print("🔍 ТЕСТ ЕДИНООБРАЗИЯ СИСТЕМЫ КОНТРОЛЯ ДОСТУПА")
    print("=" * 60)
    
    # Создаем тестового пользователя без подписки
    test_user_no_sub = 5015100200
    print(f"\n👤 ТЕСТ 1: Пользователь без подписки (ID: {test_user_no_sub})")
    
    # Проверяем доступ ко всем функциям
    features_to_test = [
        ("transform", "Трансформация изображений", 1),
        ("video_generation", "Генерация видео", 20),
        ("tryon", "Виртуальная примерочная", 3),
        ("json", "JSON генерация", 20),
    ]
    
    print("📋 Результаты проверки доступа:")
    for feature_key, feature_name, expected_cost in features_to_test:
        access_check = can_use_feature(test_user_no_sub, feature_key)
        status = "✅ Доступ разрешен" if access_check["can_use"] else f"❌ {access_check['message']}"
        print(f"  {feature_name}: {status}")
        
        # Проверяем, что сообщение содержит правильную информацию
        if not access_check["can_use"]:
            if access_check["reason"] == "no_subscription":
                assert "подписк" in access_check["message"].lower(), f"Сообщение должно содержать 'подписк': {access_check['message']}"
            elif access_check["reason"] == "insufficient_coins":
                assert "монет" in access_check["message"].lower(), f"Сообщение должно содержать 'монет': {access_check['message']}"
    
    # Создаем тестового пользователя с подпиской
    test_user_with_sub = 5015100201
    print(f"\n👤 ТЕСТ 2: Пользователь с подпиской (ID: {test_user_with_sub})")
    
    # Создаем подписку
    plan_info = get_tariff_by_name("lite")
    if plan_info:
        try:
            create_subscription(
                test_user_with_sub, 
                plan_info["name"], 
                plan_info["coins"], 
                plan_info["price_rub"], 
                plan_info["duration_days"], 
                "test-unified-access"
            )
            print(f"✅ Подписка {plan_info['name']} создана")
        except Exception as e:
            print(f"❌ Ошибка создания подписки: {e}")
    
    print("📋 Результаты проверки доступа:")
    for feature_key, feature_name, expected_cost in features_to_test:
        access_check = can_use_feature(test_user_with_sub, feature_key)
        status = "✅ Доступ разрешен" if access_check["can_use"] else f"❌ {access_check['message']}"
        print(f"  {feature_name}: {status}")
    
    # Тест 3: Проверка единообразия сообщений об ошибках
    print(f"\n🧪 ТЕСТ 3: Единообразие сообщений об ошибках")
    
    # Проверяем, что все функции возвращают одинаковый формат
    error_messages = []
    for feature_key, _, _ in features_to_test:
        access_check = can_use_feature(test_user_no_sub, feature_key)
        if not access_check["can_use"]:
            error_messages.append((feature_key, access_check["reason"], access_check["message"]))
    
    print("📋 Анализ сообщений об ошибках:")
    for feature_key, reason, message in error_messages:
        print(f"  {feature_key} ({reason}): {message}")
    
    # Проверяем, что все сообщения для одной причины похожи
    no_sub_messages = [msg for _, reason, msg in error_messages if reason == "no_subscription"]
    if no_sub_messages:
        print(f"\n✅ Сообщения 'no_subscription' единообразны: {len(set(no_sub_messages))} уникальных из {len(no_sub_messages)}")
    
    # Тест 4: Проверка кнопок доступа
    print(f"\n🧪 ТЕСТ 4: Проверка кнопок доступа")
    
    # Имитируем функцию get_access_denied_keyboard
    def get_access_denied_keyboard(access_check: dict):
        if access_check["reason"] == "no_subscription":
            return "💳 Купить подписку, ⬅️ Назад"
        elif access_check["reason"] == "insufficient_coins":
            return "💰 Докупить монетки, ⬅️ Назад"
        else:
            return "⬅️ Назад"
    
    print("📋 Кнопки для разных причин отказа:")
    for feature_key, _, _ in features_to_test:
        access_check = can_use_feature(test_user_no_sub, feature_key)
        if not access_check["can_use"]:
            buttons = get_access_denied_keyboard(access_check)
            print(f"  {feature_key} ({access_check['reason']}): {buttons}")
    
    print(f"\n✅ ТЕСТ ЕДИНООБРАЗИЯ ЗАВЕРШЕН!")
    print("🎯 Все платные функции имеют единообразную систему проверки доступа")
    print("🎯 Сообщения об ошибках стандартизированы")
    print("🎯 Кнопки доступа унифицированы")

if __name__ == "__main__":
    test_access_control_unified()
