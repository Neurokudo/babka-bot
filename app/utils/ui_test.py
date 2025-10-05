"""
UI Integrity Test Utility
Утилита для проверки целостности UI-логики бота
"""

import re
import logging
from pathlib import Path
from typing import Set, List, Dict, Tuple

log = logging.getLogger("ui_test")

def test_ui_integrity() -> List[str]:
    """
    Проверить целостность UI-логики бота
    
    Returns:
        List[str]: Список найденных проблем
    """
    errors = []
    
    try:
        # Проверяем основные файлы
        main_file = Path("main.py")
        if not main_file.exists():
            errors.append("main.py не найден")
            return errors
        
        text = main_file.read_text(encoding="utf-8", errors="ignore")
        
        # 1. Проверяем уникальность callback'ов
        callback_duplicates = find_duplicate_callbacks(text)
        if callback_duplicates:
            errors.extend([f"Дублирующийся callback: {cb}" for cb in callback_duplicates])
        
        # 2. Проверяем наличие обработчиков
        missing_handlers = find_missing_handlers(text)
        if missing_handlers:
            errors.extend([f"Отсутствует обработчик: {cb}" for cb in missing_handlers])
        
        # 3. Проверяем безопасность навигации
        nav_issues = check_navigation_safety(text)
        errors.extend(nav_issues)
        
        # 4. Проверяем критические экраны
        critical_issues = check_critical_screens(text)
        errors.extend(critical_issues)
        
    except Exception as e:
        errors.append(f"Ошибка проверки UI: {e}")
        log.error(f"UI integrity check failed: {e}")
    
    return errors

def find_duplicate_callbacks(text: str) -> List[str]:
    """Найти дублирующиеся callback'ы"""
    duplicates = []
    
    # Ищем все callback_data
    callback_pattern = r"callback_data=['\"](.*?)['\"]"
    callbacks = re.findall(callback_pattern, text)
    
    # Подсчитываем количество вхождений
    callback_counts = {}
    for callback in callbacks:
        callback_counts[callback] = callback_counts.get(callback, 0) + 1
    
    # Находим дубликаты
    for callback, count in callback_counts.items():
        if count > 1:
            duplicates.append(callback)
    
    return duplicates

def find_missing_handlers(text: str) -> List[str]:
    """Найти callback'ы без обработчиков"""
    missing = []
    
    # Находим все callback_data
    callback_pattern = r"callback_data=['\"](.*?)['\"]"
    callbacks = set(re.findall(callback_pattern, text))
    
    # Находим все обработчики
    handler_patterns = [
        r"if data == ['\"](.*?)['\"]",
        r"elif data == ['\"](.*?)['\"]",
    ]
    
    handlers = set()
    for pattern in handler_patterns:
        handlers.update(re.findall(pattern, text))
    
    # Находим отсутствующие обработчики
    missing = list(callbacks - handlers)
    
    return missing

def check_navigation_safety(text: str) -> List[str]:
    """Проверить безопасность навигации"""
    issues = []
    
    # Критичные экраны, которые должны иметь кнопку возврата
    critical_screens = [
        "show_tariffs",
        "show_profile", 
        "tryon_start",
        "menu_transforms",
        "nkudo_menu",
        "lego_menu",
        "jsonpro_menu"
    ]
    
    for screen in critical_screens:
        # Ищем обработчик этого экрана
        screen_pattern = rf"if data == ['\"]{screen}['\"]"
        if re.search(screen_pattern, text):
            # Проверяем, есть ли кнопка возврата
            handler_pattern = rf"if data == ['\"]{screen}['\"]:(.*?)(?=if data ==|elif data ==|$)"
            handler_match = re.search(handler_pattern, text, re.DOTALL)
            
            if handler_match:
                handler_text = handler_match.group(1)
                # Проверяем наличие кнопок возврата
                back_patterns = [
                    r"callback_data=['\"](back_|home|main)",
                    r"Назад",
                    r"Главное меню",
                    r"⬅️"
                ]
                
                has_back = any(re.search(pattern, handler_text) for pattern in back_patterns)
                if not has_back:
                    issues.append(f"Экран '{screen}' не имеет кнопки возврата")
    
    return issues

def check_critical_screens(text: str) -> List[str]:
    """Проверить критические экраны"""
    issues = []
    
    # Проверяем наличие ключевых функций
    critical_functions = [
        "kb_home_inline",
        "kb_tariffs", 
        "kb_profile",
        "kb_tryon_start",
        "kb_transform_quality"
    ]
    
    for func in critical_functions:
        func_pattern = rf"def {func}\("
        if not re.search(func_pattern, text):
            issues.append(f"Отсутствует критичная функция: {func}")
    
    # Проверяем наличие ключевых обработчиков
    critical_handlers = [
        "show_tariffs",
        "show_profile",
        "tryon_start", 
        "menu_transforms"
    ]
    
    for handler in critical_handlers:
        handler_pattern = rf"if data == ['\"]{handler}['\"]"
        if not re.search(handler_pattern, text):
            issues.append(f"Отсутствует критичный обработчик: {handler}")
    
    return issues

def validate_keyboard_function(func_name: str, func_text: str) -> List[str]:
    """Валидировать функцию создания клавиатуры"""
    issues = []
    
    # Проверяем, что функция возвращает InlineKeyboardMarkup
    if "InlineKeyboardMarkup" not in func_text:
        issues.append(f"Функция {func_name} не возвращает InlineKeyboardMarkup")
    
    # Проверяем наличие callback_data в кнопках
    callback_pattern = r"callback_data=['\"](.*?)['\"]"
    callbacks = re.findall(callback_pattern, func_text)
    
    if not callbacks:
        issues.append(f"Функция {func_name} не содержит callback_data")
    
    # Проверяем, что все callback'ы имеют обработчики
    # (это будет проверено в основной функции)
    
    return issues

def get_ui_statistics() -> Dict[str, int]:
    """Получить статистику UI"""
    stats = {
        "total_callbacks": 0,
        "total_handlers": 0,
        "total_keyboards": 0,
        "duplicate_callbacks": 0,
        "missing_handlers": 0
    }
    
    try:
        text = Path("main.py").read_text(encoding="utf-8", errors="ignore")
        
        # Подсчитываем callback'ы
        callback_pattern = r"callback_data=['\"](.*?)['\"]"
        callbacks = re.findall(callback_pattern, text)
        stats["total_callbacks"] = len(set(callbacks))
        
        # Подсчитываем обработчики
        handler_patterns = [
            r"if data == ['\"](.*?)['\"]",
            r"elif data == ['\"](.*?)['\"]",
        ]
        
        handlers = set()
        for pattern in handler_patterns:
            handlers.update(re.findall(pattern, text))
        stats["total_handlers"] = len(handlers)
        
        # Подсчитываем клавиатуры
        kb_pattern = r"def (kb_[a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):"
        keyboards = re.findall(kb_pattern, text)
        stats["total_keyboards"] = len(keyboards)
        
        # Подсчитываем проблемы
        stats["duplicate_callbacks"] = len(find_duplicate_callbacks(text))
        stats["missing_handlers"] = len(find_missing_handlers(text))
        
    except Exception as e:
        log.error(f"Failed to get UI statistics: {e}")
    
    return stats

def startup_integrity_check():
    """Проверка целостности UI при запуске бота"""
    try:
        errors = test_ui_integrity()
        if errors:
            log.warning(f"[UI CHECK] Обнаружены проблемы: {errors}")
            # Не прерываем работу бота, только логируем
        else:
            log.info("[UI CHECK] Все callback'ы и кнопки валидны")
        
        # Логируем статистику
        stats = get_ui_statistics()
        log.info(f"[UI STATS] Callbacks: {stats['total_callbacks']}, "
                f"Handlers: {stats['total_handlers']}, "
                f"Keyboards: {stats['total_keyboards']}")
        
    except Exception as e:
        log.error(f"[UI CHECK] Ошибка проверки целостности: {e}")
