#!/usr/bin/env python3
"""
Автотест UI системы для проверки корректности форматирования тарифов и кнопок
"""
import sys
import os

# Добавляем корневую папку проекта в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pricing import format_plans_list, get_available_tariffs, format_topup_packs, get_available_topup_packs

def test_pricing_smoke():
    """Smoke-тест для проверки основных функций pricing"""
    print("🧪 Запуск smoke-тестов UI системы...")

    # Тест форматирования тарифов
    try:
        t = format_plans_list()
        print(f"✅ format_plans_list() работает: {len(t)} символов")

        # Проверяем наличие ключевых слов
        assert "монет" in t, "В тексте тарифов должны быть монеты"
        assert ("1990" in t or "1 990" in t), "Должен быть тариф за 1990 руб"

        print("✅ Текст тарифов содержит ожидаемые элементы")

    except Exception as e:
        print(f"❌ Ошибка в format_plans_list(): {e}")
        return False

    # Тест получения тарифов
    try:
        tariffs = get_available_tariffs()
        print(f"✅ get_available_tariffs() вернул {len(tariffs)} тарифов")

        # Проверяем обязательные тарифы
        tariff_names = [t["name"] for t in tariffs]
        required_tariffs = ["lite", "standard", "pro"]
        for tariff in required_tariffs:
            assert tariff in tariff_names, f"Должен быть тариф '{tariff}'"

        # Выводим информацию о тарифах
        for tariff in tariffs:
            print(f"✅ Тариф '{tariff['name']}': {tariff['title']} — {tariff['price_rub']} ₽ → {tariff['coins']} монет")

    except Exception as e:
        print(f"❌ Ошибка в get_available_tariffs(): {e}")
        return False

    # Тест форматирования пакетов монет
    try:
        tp = format_topup_packs()
        print(f"✅ format_topup_packs() работает: {len(tp)} символов")

        # Проверяем наличие монет в тексте
        assert "монет" in tp, "В тексте пакетов должны быть монеты"

    except Exception as e:
        print(f"❌ Ошибка в format_topup_packs(): {e}")
        return False

    # Тест получения пакетов монет
    try:
        topup_packs = get_available_topup_packs()
        print(f"✅ get_available_topup_packs() вернул {len(topup_packs)} пакетов")

        for pack in topup_packs:
            coins = pack['coins']
            price = pack['price_rub']
            rate = pack['rate_rub_per_coin']
            print(f"✅ Пакет: {coins} монет — {price} ₽ (ставка: {rate:.2f} ₽/монета)")

    except Exception as e:
        print(f"❌ Ошибка в get_available_topup_packs(): {e}")
        return False

    print("🎉 Все smoke-тесты UI системы прошли успешно!")
    return True

if __name__ == "__main__":
    success = test_pricing_smoke()
    sys.exit(0 if success else 1)
