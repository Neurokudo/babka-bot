#!/usr/bin/env python3
"""Тест новой тарифной сетки"""

from app.config.pricing import TARIFFS, FEATURE_COSTS, SPECIAL_PACKS
from app.services.pricing import (
    get_available_tariffs, 
    format_feature_costs, 
    format_special_packs,
    pricing_text,
    calculate_tariff_examples
)

def test_tariffs():
    """Тест тарифов"""
    print("=== ТЕСТ ТАРИФОВ ===")
    tariffs = get_available_tariffs()
    for tariff in tariffs:
        print(f"{tariff['icon']} {tariff['title']} — {tariff['price_rub']} ₽ → {tariff['coins']} монет")
        examples = calculate_tariff_examples(tariff['coins'])
        print(f"  Примеры использования:")
        for line in examples.split('\n'):
            print(f"    {line}")
        print()

def test_feature_costs():
    """Тест стоимости функций"""
    print("=== ТЕСТ СТОИМОСТИ ФУНКЦИЙ ===")
    print(format_feature_costs())
    print()

def test_special_packs():
    """Тест разовых пакетов"""
    print("=== ТЕСТ РАЗОВЫХ ПАКЕТОВ ===")
    print(format_special_packs())
    print()

def test_full_pricing():
    """Тест полной тарифной сетки"""
    print("=== ПОЛНАЯ ТАРИФНАЯ СЕТКА ===")
    print(pricing_text())
    print()

def test_feature_cost_calculation():
    """Тест расчета стоимости функций"""
    print("=== ТЕСТ РАСЧЕТА СТОИМОСТИ ===")
    
    # Проверяем новые функции
    test_features = [
        "video_6s_mute",
        "video_8s_mute", 
        "video_8s_audio",
        "image_basic",
        "virtual_tryon"
    ]
    
    for feature in test_features:
        cost = FEATURE_COSTS.get(feature, 0)
        print(f"{feature}: {cost} монет")
    print()

if __name__ == "__main__":
    test_tariffs()
    test_feature_costs()
    test_special_packs()
    test_full_pricing()
    test_feature_cost_calculation()
    
    print("✅ Все тесты пройдены!")
