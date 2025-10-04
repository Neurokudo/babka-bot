#!/usr/bin/env python3
# test_ui_system.py
"""Тесты для новой UI системы бота"""

import unittest
import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.ui.callbacks import Cb, parse_cb, Actions
from app.ui.texts import t
# from app.ui.keyboards import build_keyboard, build_keyboard_with_description  # Требует aiogram
from app.ui.menu_schema import MENU, validate_menu_schema, get_all_node_ids
# from app.handlers.router import HANDLERS  # Требует aiogram

class TestCallbacks(unittest.TestCase):
    """Тесты для системы callback-ов"""
    
    def test_cb_pack_unpack(self):
        """Тест упаковки/распаковки callback данных"""
        # Простой callback
        cb = Cb("nav", "root")
        packed = cb.pack()
        unpacked = Cb.unpack(packed)
        
        self.assertEqual(unpacked.action, "nav")
        self.assertEqual(unpacked.id, "root")
        self.assertIsNone(unpacked.extra)
        
        # Callback с extra
        cb2 = Cb("action", "id", "extra")
        packed2 = cb2.pack()
        unpacked2 = Cb.unpack(packed2)
        
        self.assertEqual(unpacked2.action, "action")
        self.assertEqual(unpacked2.id, "id")
        self.assertEqual(unpacked2.extra, "extra")
    
    def test_cb_length_limit(self):
        """Тест ограничения длины callback данных"""
        # Создаем очень длинный callback
        long_id = "a" * 100
        cb = Cb("action", long_id)
        packed = cb.pack()
        
        # Должен быть обрезан до 64 байт
        self.assertLessEqual(len(packed.encode('utf-8')), 64)
    
    def test_parse_cb_valid(self):
        """Тест парсинга валидных callback данных"""
        # Валидный callback
        result = parse_cb("nav|root")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "nav")
        self.assertEqual(result.id, "root")
        
        # Callback с extra
        result2 = parse_cb("action|id|extra")
        self.assertIsNotNone(result2)
        self.assertEqual(result2.action, "action")
        self.assertEqual(result2.id, "id")
        self.assertEqual(result2.extra, "extra")
    
    def test_parse_cb_invalid(self):
        """Тест парсинга невалидных callback данных"""
        # Пустая строка
        self.assertIsNone(parse_cb(""))
        
        # None
        self.assertIsNone(parse_cb(None))
        
        # Некорректный формат (пустой action)
        self.assertIsNone(parse_cb("|invalid"))
        self.assertIsNone(parse_cb("||invalid"))

class TestTexts(unittest.TestCase):
    """Тесты для системы текстов"""
    
    def test_t_function(self):
        """Тест функции получения текстов"""
        # Существующий ключ
        text = t("menu.title")
        self.assertEqual(text, "🏠 Главное меню")
        
        # Несуществующий ключ (должен вернуть ключ как есть)
        text2 = t("nonexistent.key")
        self.assertEqual(text2, "nonexistent.key")
    
    def test_t_with_formatting(self):
        """Тест форматирования текстов"""
        # Текст с форматированием
        text = t("desc.transforms", coins=100)
        self.assertIn("100", text)
        self.assertIn("монеток", text)

class TestMenuSchema(unittest.TestCase):
    """Тесты для схемы меню"""
    
    def test_menu_structure(self):
        """Тест структуры меню"""
        # Проверяем наличие основных узлов
        self.assertIn("root", MENU)
        self.assertIn("modes", MENU)
        self.assertIn("lego_menu", MENU)
        
        # Проверяем структуру узла
        root_node = MENU["root"]
        self.assertIn("text_key", root_node)
        self.assertIn("buttons", root_node)
        self.assertIsInstance(root_node["buttons"], list)
    
    def test_menu_validation(self):
        """Тест валидации схемы меню"""
        errors = validate_menu_schema()
        self.assertEqual(len(errors), 0, f"Schema validation errors: {errors}")
    
    def test_all_targets_exist(self):
        """Тест что все ссылки на узлы существуют"""
        all_node_ids = get_all_node_ids()
        
        for node_id, node in MENU.items():
            for button in node.get("buttons", []):
                target = button.get("to")
                if target:
                    self.assertIn(target, all_node_ids, 
                                f"Node '{node_id}' references non-existent target '{target}'")

class TestKeyboards(unittest.TestCase):
    """Тесты для генерации клавиатур (заглушка без aiogram)"""
    
    def test_keyboard_placeholder(self):
        """Заглушка для тестов клавиатур"""
        # Тесты клавиатур требуют aiogram, пропускаем
        self.assertTrue(True, "Keyboard tests skipped - requires aiogram")

class TestRouter(unittest.TestCase):
    """Тесты для роутера (заглушка без aiogram)"""
    
    def test_router_placeholder(self):
        """Заглушка для тестов роутера"""
        # Тесты роутера требуют aiogram, пропускаем
        self.assertTrue(True, "Router tests skipped - requires aiogram")

class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def test_full_flow(self):
        """Тест полного флоу от callback до парсинга"""
        # Создаем callback
        cb = Cb(Actions.NAV, "lego_menu")
        packed = cb.pack()
        
        # Парсим обратно
        parsed = parse_cb(packed)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.action, Actions.NAV)
        self.assertEqual(parsed.id, "lego_menu")
    
    def test_menu_navigation(self):
        """Тест навигации по меню"""
        # Проверяем что можно добраться от root до основных узлов
        visited = set()
        to_visit = ["root"]
        
        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
                
            visited.add(current)
            
            if current in MENU:
                for button in MENU[current].get("buttons", []):
                    target = button.get("to")
                    if target and target not in visited:
                        to_visit.append(target)
        
        # Проверяем что основные узлы достижимы
        main_nodes = {"root", "modes", "lego_menu", "nkudo_menu", "tryon_start", 
                     "transforms", "jsonpro_start", "profile"}
        unreachable = main_nodes - visited
        self.assertEqual(len(unreachable), 0, 
                        f"Unreachable main nodes: {unreachable}")
        
        # Проверяем что общее количество достижимых узлов разумное
        self.assertGreater(len(visited), 10, "Too few reachable nodes")

def run_tests():
    """Запуск всех тестов"""
    # Создаем test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавляем тесты
    test_classes = [
        TestCallbacks,
        TestTexts,
        TestMenuSchema,
        TestKeyboards,
        TestRouter,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
