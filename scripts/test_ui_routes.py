#!/usr/bin/env python3
"""
UI Routes Test Script
Проверяет целостность всех кнопок и callback'ов в боте
"""

import re
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple

def find_callbacks() -> Set[str]:
    """Найти все callback_data в проекте"""
    callbacks = set()
    
    # Ищем в основных файлах
    search_paths = [
        "main.py",
        "app/ui/",
        "app/handlers/",
        "app/"
    ]
    
    for search_path in search_paths:
        if Path(search_path).is_file():
            # Одиночный файл
            files = [Path(search_path)]
        else:
            # Директория
            files = list(Path(search_path).rglob("*.py"))
        
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                
                # Ищем callback_data в различных форматах
                patterns = [
                    r"callback_data=['\"](.*?)['\"]",  # callback_data="value"
                    r"callback_data=([a-zA-Z_][a-zA-Z0-9_]*)",  # callback_data=variable
                    r"CallbackQueryHandler\(.*?['\"](.*?)['\"]",  # CallbackQueryHandler("value")
                ]
                
                for pattern in patterns:
                    for match in re.findall(pattern, text):
                        if isinstance(match, str) and match.strip():
                            callbacks.add(match.strip())
                            
            except Exception as e:
                print(f"⚠️ Ошибка чтения файла {file}: {e}")
    
    return callbacks

def find_handlers() -> Set[str]:
    """Найти все зарегистрированные обработчики callback'ов"""
    handlers = set()
    
    # Ищем в main.py и handlers/
    search_paths = ["main.py", "app/handlers/"]
    
    for search_path in search_paths:
        if Path(search_path).is_file():
            files = [Path(search_path)]
        else:
            files = list(Path(search_path).rglob("*.py"))
        
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                
                # Ищем обработчики в различных форматах
                patterns = [
                    r"if data == ['\"](.*?)['\"]",  # if data == "value"
                    r"elif data == ['\"](.*?)['\"]",  # elif data == "value"
                    r"CallbackQueryHandler\(.*?['\"](.*?)['\"]",  # CallbackQueryHandler("value")
                    r"callback_data=['\"](.*?)['\"]",  # callback_data в обработчиках
                ]
                
                for pattern in patterns:
                    for match in re.findall(pattern, text):
                        if isinstance(match, str) and match.strip():
                            handlers.add(match.strip())
                            
            except Exception as e:
                print(f"⚠️ Ошибка чтения файла {file}: {e}")
    
    return handlers

def find_keyboard_functions() -> Dict[str, List[str]]:
    """Найти все функции создания клавиатур и их callback'ы"""
    keyboards = {}
    
    # Ищем функции kb_* в main.py
    try:
        text = Path("main.py").read_text(encoding="utf-8", errors="ignore")
        
        # Ищем функции def kb_*():
        kb_pattern = r"def (kb_[a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):"
        kb_functions = re.findall(kb_pattern, text)
        
        for func_name in kb_functions:
            # Ищем callback_data в этой функции
            func_pattern = rf"def {func_name}\([^)]*\):(.*?)(?=def |$)"
            func_match = re.search(func_pattern, text, re.DOTALL)
            
            if func_match:
                func_text = func_match.group(1)
                callbacks = re.findall(r"callback_data=['\"](.*?)['\"]", func_text)
                keyboards[func_name] = callbacks
                
    except Exception as e:
        print(f"⚠️ Ошибка анализа клавиатур: {e}")
    
    return keyboards

def check_navigation_safety() -> List[str]:
    """Проверить безопасность навигации"""
    issues = []
    
    try:
        text = Path("main.py").read_text(encoding="utf-8", errors="ignore")
        
        # Критичные экраны, которые должны иметь кнопку возврата
        critical_screens = [
            "show_tariffs",
            "show_profile", 
            "tryon_start",
            "menu_transforms",
            "nkudo_menu",
            "lego_menu"
        ]
        
        for screen in critical_screens:
            # Ищем обработчик этого экрана
            screen_pattern = rf"if data == ['\"]{screen}['\"]"
            if re.search(screen_pattern, text):
                # Проверяем, есть ли кнопка возврата в клавиатуре
                # Ищем функцию клавиатуры после этого обработчика
                handler_pattern = rf"if data == ['\"]{screen}['\"]:(.*?)(?=if data ==|elif data ==|$)"
                handler_match = re.search(handler_pattern, text, re.DOTALL)
                
                if handler_match:
                    handler_text = handler_match.group(1)
                    # Проверяем наличие кнопок возврата
                    back_patterns = [
                        r"callback_data=['\"](back_|home|main)",
                        r"Назад",
                        r"Главное меню"
                    ]
                    
                    has_back = any(re.search(pattern, handler_text) for pattern in back_patterns)
                    if not has_back:
                        issues.append(f"⚠️ Экран '{screen}' не имеет кнопки возврата")
                        
    except Exception as e:
        issues.append(f"⚠️ Ошибка проверки навигации: {e}")
    
    return issues

def main():
    """Основная функция тестирования"""
    print("🧭 UI ROUTES TEST")
    print("=" * 50)
    
    # Находим все callback'ы и обработчики
    callbacks = find_callbacks()
    handlers = find_handlers()
    keyboards = find_keyboard_functions()
    
    print(f"📊 Найдено callback'ов: {len(callbacks)}")
    print(f"📊 Найдено обработчиков: {len(handlers)}")
    print(f"📊 Найдено клавиатур: {len(keyboards)}")
    print()
    
    # Проверяем отсутствующие обработчики
    missing = callbacks - handlers
    if missing:
        print("❌ НЕ НАЙДЕНЫ ОБРАБОТЧИКИ:")
        for callback in sorted(missing):
            print(f"   - {callback}")
        print()
    else:
        print("✅ Все callback'ы имеют обработчики")
        print()
    
    # Проверяем неиспользуемые обработчики
    unused = handlers - callbacks
    if unused:
        print("⚠️ ОБРАБОТЧИКИ БЕЗ КНОПОК:")
        for handler in sorted(unused):
            print(f"   - {handler}")
        print()
    else:
        print("✅ Все обработчики используются")
        print()
    
    # Проверяем дублирующиеся callback'ы
    duplicates = []
    callback_counts = {}
    for callback in callbacks:
        callback_counts[callback] = callback_counts.get(callback, 0) + 1
    
    for callback, count in callback_counts.items():
        if count > 1:
            duplicates.append(callback)
    
    if duplicates:
        print("❌ ДУБЛИРУЮЩИЕСЯ CALLBACK'Ы:")
        for callback in sorted(duplicates):
            print(f"   - {callback} (встречается {callback_counts[callback]} раз)")
        print()
    else:
        print("✅ Нет дублирующихся callback'ов")
        print()
    
    # Проверяем безопасность навигации
    nav_issues = check_navigation_safety()
    if nav_issues:
        print("⚠️ ПРОБЛЕМЫ НАВИГАЦИИ:")
        for issue in nav_issues:
            print(f"   {issue}")
        print()
    else:
        print("✅ Навигация безопасна")
        print()
    
    # Проверяем клавиатуры
    if keyboards:
        print("⌨️ АНАЛИЗ КЛАВИАТУР:")
        for kb_name, kb_callbacks in keyboards.items():
            print(f"   {kb_name}: {len(kb_callbacks)} кнопок")
            for callback in kb_callbacks:
                if callback not in handlers:
                    print(f"     ❌ {callback} - нет обработчика")
        print()
    
    # Итоговый результат
    total_issues = len(missing) + len(duplicates) + len(nav_issues)
    
    if total_issues == 0:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ UI-логика бота в порядке")
        return 0
    else:
        print(f"❌ ОБНАРУЖЕНО {total_issues} ПРОБЛЕМ")
        print("⚠️ Требуется исправление перед деплоем")
        return 1

if __name__ == "__main__":
    sys.exit(main())
