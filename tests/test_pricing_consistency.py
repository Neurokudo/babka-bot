# -*- coding: utf-8 -*-
"""
Тесты для проверки консистентности тарифов и отсутствия старых формулировок
"""

import pytest
from app.services.pricing import (
    format_plans_list,
    format_feature_costs,
    pricing_text,
    get_available_tariffs,
    get_available_features,
    feature_cost_coins
)


class TestPricingConsistency:
    """Тесты консистентности тарифов"""
    
    def test_format_plans_list_no_old_formulations(self):
        """Проверяем, что в списке тарифов нет старых формулировок"""
        plans_text = format_plans_list()
        
        # Проверяем отсутствие старых формулировок типа "10 видео + 20 фото"
        assert "10 видео" not in plans_text
        assert "20 фото" not in plans_text
        assert "10 video" not in plans_text
        assert "20 photo" not in plans_text
        
        # Проверяем наличие монет
        assert "монет" in plans_text
        assert "монета" in plans_text
        
        # Проверяем наличие тарифов (количество монет)
        tariffs = get_available_tariffs()
        for tariff_name, tariff in tariffs.items():
            assert str(tariff.coins) in plans_text
            # Цены форматируются с запятыми
            assert f"{tariff.price_rub:,}" in plans_text
    
    def test_format_feature_costs_uses_coins_only(self):
        """Проверяем, что стоимость функций отображается только в монетах"""
        costs_text = format_feature_costs()
        
        # Проверяем отсутствие старых формулировок типа "10 видео + 20 фото"
        assert "10 видео" not in costs_text
        assert "20 фото" not in costs_text
        assert "10 video" not in costs_text
        assert "20 photo" not in costs_text
        
        # Проверяем наличие монет
        assert "монет" in costs_text
        assert "монета" in costs_text
        
        # Проверяем наличие всех функций
        features = get_available_features()
        for feature_key in features.keys():
            cost = feature_cost_coins(feature_key)
            assert str(cost) in costs_text
    
    def test_pricing_text_consistency(self):
        """Проверяем общий текст тарифов на консистентность"""
        full_text = pricing_text()
        
        # Проверяем отсутствие старых формулировок типа "10 видео + 20 фото"
        assert "10 видео" not in full_text
        assert "20 фото" not in full_text
        assert "10 video" not in full_text
        assert "20 photo" not in full_text
        
        # Проверяем наличие монет
        assert "монет" in full_text
        assert "монета" in full_text
        
        # Проверяем, что текст содержит и тарифы, и стоимость функций
        assert "Тарифы" in full_text
        assert "Видео" in full_text
        assert "Фото-инструменты" in full_text
        assert "Примерка одежды" in full_text
    
    def test_tariff_prices_match_config(self):
        """Проверяем, что цены тарифов соответствуют конфигурации"""
        tariffs = get_available_tariffs()
        
        # Проверяем конкретные тарифы
        assert "lite" in tariffs
        assert "standard" in tariffs
        assert "pro" in tariffs
        
        # Проверяем цены
        assert tariffs["lite"].price_rub == 1990
        assert tariffs["lite"].coins == 120
        
        assert tariffs["standard"].price_rub == 2490
        assert tariffs["standard"].coins == 210
        
        assert tariffs["pro"].price_rub == 4990
        assert tariffs["pro"].coins == 440
    
    def test_feature_costs_match_config(self):
        """Проверяем, что стоимость функций соответствует конфигурации"""
        features = get_available_features()
        
        # Проверяем конкретные функции
        assert "video_8s_audio" in features
        assert "video_8s_mute" in features
        assert "image_basic" in features
        assert "virtual_tryon" in features
        
        # Проверяем стоимость
        assert features["video_8s_audio"] == 20
        assert features["video_8s_mute"] == 16
        assert features["image_basic"] == 1
        assert features["virtual_tryon"] == 3
    
    def test_no_hardcoded_old_values(self):
        """Проверяем отсутствие хардкоженных старых значений"""
        plans_text = format_plans_list()
        costs_text = format_feature_costs()
        
        # Проверяем отсутствие старых значений
        old_values = ["10 видео", "20 фото", "10 video", "20 photo"]
        for old_value in old_values:
            assert old_value not in plans_text
            assert old_value not in costs_text
    
    def test_coin_rate_calculation(self):
        """Проверяем правильность расчета курса монет"""
        from app.services.pricing import calculate_coin_rate_rub
        
        # Проверяем курс для каждого тарифа
        lite_rate = calculate_coin_rate_rub("lite")
        assert abs(lite_rate - 16.58) < 0.1  # ~16.6 ₽/монета
        
        standard_rate = calculate_coin_rate_rub("standard")
        assert abs(standard_rate - 11.86) < 0.1  # ~11.9 ₽/монета
        
        pro_rate = calculate_coin_rate_rub("pro")
        assert abs(pro_rate - 11.34) < 0.1  # ~11.3 ₽/монета
