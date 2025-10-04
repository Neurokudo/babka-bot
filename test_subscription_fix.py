#!/usr/bin/env python3
"""
Скрипт для тестирования исправленной подписки
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.db_subscriptions import db_conn
from app.services.billing import check_subscription
from app.services.pricing import get_available_tariffs

def test_subscription_fix():
    """Тестируем исправленную подписку"""
    user_id = 5015100177
    
    print("🔍 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ПОДПИСКИ")
    print("=" * 50)
    
    # 1. Проверяем данные в базе
    print("\n1️⃣ ПРОВЕРКА БАЗЫ ДАННЫХ:")
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT plan, plan_expiry, coins, auto_renew FROM users WHERE user_id = ?', (user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            plan, expiry, coins, auto_renew = user_data
            print(f"   ✅ Plan: {plan}")
            print(f"   ✅ Expiry: {expiry}")
            print(f"   ✅ Coins: {coins}")
            print(f"   ✅ Auto_renew: {auto_renew}")
        else:
            print("   ❌ Пользователь не найден в базе!")
            return
    
    # 2. Проверяем функцию check_subscription
    print("\n2️⃣ ПРОВЕРКА ФУНКЦИИ check_subscription:")
    subscription_data = check_subscription(user_id)
    print(f"   ✅ User ID: {subscription_data.get('user_id')}")
    print(f"   ✅ Plan: {subscription_data.get('plan')}")
    print(f"   ✅ Coins: {subscription_data.get('coins')}")
    print(f"   ✅ Is Active: {subscription_data.get('is_active')}")
    print(f"   ✅ Source: {subscription_data.get('source')}")
    
    # 3. Проверяем тарифы
    print("\n3️⃣ ПРОВЕРКА ТАРИФОВ:")
    tariffs = get_available_tariffs()
    pro_tariff = next((t for t in tariffs if t["name"] == "pro"), None)
    
    if pro_tariff:
        print(f"   ✅ Pro тариф найден:")
        print(f"      - Название: {pro_tariff['title']}")
        print(f"      - Цена: {pro_tariff['price_rub']} RUB")
        print(f"      - Монеты: {pro_tariff['coins']}")
    else:
        print("   ❌ Pro тариф не найден!")
    
    # 4. Проверяем активные подписки
    print("\n4️⃣ АКТИВНЫЕ ПОДПИСКИ:")
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT plan, coins, price_rub, start_date, end_date, payment_id FROM subscriptions WHERE user_id = ? AND is_active = 1', (user_id,))
        active_subs = cur.fetchall()
        
        if active_subs:
            for sub in active_subs:
                plan, coins, price, start, end, payment = sub
                print(f"   ✅ Plan: {plan}, Coins: {coins}, Price: {price} RUB")
                print(f"      Start: {start}, End: {end}")
                print(f"      Payment ID: {payment}")
        else:
            print("   ❌ Активных подписок не найдено!")
    
    # 5. Итоговый результат
    print("\n5️⃣ ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    if subscription_data.get('plan') == 'pro' and subscription_data.get('coins') == 440:
        print("   🎉 УСПЕХ! Подписка Pro исправлена корректно!")
        print("   ✅ Тариф: Pro")
        print("   ✅ Монеты: 440")
        print("   ✅ Статус: Активна")
    else:
        print("   ❌ ОШИБКА! Подписка не исправлена корректно!")
        print(f"   Текущий план: {subscription_data.get('plan')}")
        print(f"   Текущие монеты: {subscription_data.get('coins')}")

if __name__ == "__main__":
    test_subscription_fix()
