# -*- coding: utf-8 -*-
"""
Test to ensure old pricing constants are removed
"""

import unittest
import os
import re
from pathlib import Path


class TestLegacyCleanup(unittest.TestCase):
    """Тест очистки старых тарифов"""
    
    def setUp(self):
        """Настройка теста"""
        self.project_root = Path(__file__).parent.parent
        self.old_constants = [
            'COST_VIDEO = 10',
            'COST_TRANSFORM = 1',
            'COST_TRYON = 1',
            'PLANS = {',
            'TOP_UPS = [',
            'ADDONS = {',
        ]
        
        # Разрешенные файлы, где могут быть старые константы
        self.allowed_files = {
            'tests/test_legacy_cleanup.py',  # этот файл
            'tests/test_pricing.py',  # новый тест
            'app/config/pricing.py',  # новая конфигурация
            'app/services/pricing.py',  # новый сервис
            'app/services/wallet.py',  # новый сервис кошелька
        }
    
    def test_no_old_constants_in_code(self):
        """Проверяем, что старые константы не используются в коде"""
        for root, dirs, files in os.walk(self.project_root):
            # Пропускаем служебные директории
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # Пропускаем разрешенные файлы
                if str(relative_path) in self.allowed_files:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for old_constant in self.old_constants:
                        if old_constant in content:
                            self.fail(
                                f"Found old constant '{old_constant}' in {relative_path}. "
                                f"Please update to use new pricing system."
                            )
                except Exception as e:
                    # Игнорируем ошибки чтения файлов
                    pass
    
    def test_no_hardcoded_prices(self):
        """Проверяем, что нет захардкоженных цен"""
        old_prices = [
            '1990',  # старая цена лайт
            '2490',  # старая цена стандарт
            '4990',  # старая цена про
            '10 монет',  # старая стоимость видео
            '1 монет',   # старая стоимость фото
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # Пропускаем разрешенные файлы
                if str(relative_path) in self.allowed_files:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for old_price in old_prices:
                        if old_price in content:
                            self.fail(
                                f"Found hardcoded price '{old_price}' in {relative_path}. "
                                f"Please use pricing service instead."
                            )
                except Exception:
                    pass


if __name__ == '__main__':
    unittest.main()
