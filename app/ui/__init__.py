# app/ui/__init__.py
"""UI модули для бота"""

from .texts import t
from .callbacks import Cb, parse_cb, Actions
from .menu_schema import MENU, get_menu_node, validate_menu_schema

# Импорты с зависимостями только при необходимости
def get_keyboard_functions():
    """Получить функции клавиатур (требует aiogram)"""
    try:
        from .keyboards import build_keyboard, build_keyboard_with_description
        return build_keyboard, build_keyboard_with_description
    except ImportError:
        return None, None

__all__ = [
    't', 'Cb', 'parse_cb', 'Actions',
    'MENU', 'get_menu_node', 'validate_menu_schema',
    'get_keyboard_functions'
]
