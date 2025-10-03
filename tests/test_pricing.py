# -*- coding: utf-8 -*-
"""
Unit tests for new pricing system
"""

import unittest
from app.services.pricing import (
    coins_for_tariff, price_rub_for_tariff, feature_cost_coins,
    topup_price_rub, calculate_coin_rate_rub, calculate_coin_rate_rub_topup
)
from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS_RUB


class TestPricingSystem(unittest.TestCase):
    """Тесты для новой системы тарифов"""
    
    def test_tariff_costs(self):
        """Тест стоимости тарифов"""
        self.assertEqual(coins_for_tariff('lite'), 120)
        self.assertEqual(coins_for_tariff('standard'), 210)
        self.assertEqual(coins_for_tariff('pro'), 440)
        
        self.assertEqual(price_rub_for_tariff('lite'), 1990)
        self.assertEqual(price_rub_for_tariff('standard'), 2490)
        self.assertEqual(price_rub_for_tariff('pro'), 4990)
    
    def test_feature_costs(self):
        """Тест стоимости функций"""
        self.assertEqual(feature_cost_coins('video_8s_audio'), 20)
        self.assertEqual(feature_cost_coins('video_8s_mute'), 16)
        self.assertEqual(feature_cost_coins('image_basic'), 1)
        self.assertEqual(feature_cost_coins('virtual_tryon'), 3)
    
    def test_topup_packs(self):
        """Тест пакетов пополнения"""
        self.assertEqual(topup_price_rub(50), 990)
        self.assertEqual(topup_price_rub(120), 1990)
        self.assertEqual(topup_price_rub(250), 3990)
        self.assertEqual(topup_price_rub(500), 7490)
    
    def test_coin_rates(self):
        """Тест расчета стоимости монеты"""
        # Лайт: 1990 / 120 ≈ 16.5833 ₽
        lite_rate = calculate_coin_rate_rub('lite')
        self.assertAlmostEqual(lite_rate, 16.5833, places=3)
        
        # Стандарт: 2490 / 210 ≈ 11.8571 ₽
        standard_rate = calculate_coin_rate_rub('standard')
        self.assertAlmostEqual(standard_rate, 11.8571, places=3)
        
        # Про: 4990 / 440 ≈ 11.3409 ₽
        pro_rate = calculate_coin_rate_rub('pro')
        self.assertAlmostEqual(pro_rate, 11.3409, places=3)
        
        # Пакет 250 монет: 3990 / 250 = 15.96 ₽
        topup_rate = calculate_coin_rate_rub_topup(250)
        self.assertAlmostEqual(topup_rate, 15.96, places=2)
    
    def test_config_consistency(self):
        """Тест консистентности конфигурации"""
        # Проверяем, что все тарифы имеют положительные значения
        for tariff_name, tariff in TARIFFS.items():
            self.assertGreater(tariff.price_rub, 0, f"Price for {tariff_name} should be positive")
            self.assertGreater(tariff.coins, 0, f"Coins for {tariff_name} should be positive")
        
        # Проверяем, что все функции имеют положительную стоимость
        for feature, cost in FEATURE_COSTS.items():
            self.assertGreater(cost, 0, f"Cost for {feature} should be positive")
        
        # Проверяем, что все пакеты пополнения имеют положительные значения
        for coins, price in TOPUP_PACKS_RUB.items():
            self.assertGreater(coins, 0, f"Coins for pack {coins} should be positive")
            self.assertGreater(price, 0, f"Price for pack {coins} should be positive")


if __name__ == '__main__':
    unittest.main()
