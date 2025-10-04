# app/ui/keyboards.py
"""Генерация клавиатур из декларативной схемы меню"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.ui.texts import t
from app.ui.callbacks import Cb
from app.ui.menu_schema import get_menu_node
import logging

log = logging.getLogger(__name__)

def build_keyboard(node_id: str, lang: str = "ru", **kwargs) -> InlineKeyboardMarkup:
    """Построить клавиатуру для узла меню"""
    node = get_menu_node(node_id)
    if not node:
        log.error(f"Menu node '{node_id}' not found")
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    rows = []
    buttons = node.get("buttons", [])
    
    for button_config in buttons:
        try:
            # Получаем текст кнопки
            text_key = button_config.get("text_key")
            if not text_key:
                log.warning(f"Button in node '{node_id}' missing text_key")
                continue
            
            text = t(text_key, lang, **kwargs)
            
            # Формируем callback данные
            cb_config = button_config.get("cb")
            if not cb_config:
                log.warning(f"Button '{text_key}' in node '{node_id}' missing cb config")
                continue
            
            cb = Cb(*cb_config)
            callback_data = cb.pack()
            
            # Проверяем длину callback_data
            if len(callback_data.encode('utf-8')) > 64:
                log.error(f"Callback data too long for button '{text_key}': {callback_data}")
                continue
            
            # Создаем кнопку
            button = InlineKeyboardButton(text=text, callback_data=callback_data)
            rows.append([button])  # Каждая кнопка в отдельном ряду
            
        except Exception as e:
            log.error(f"Error building button for node '{node_id}': {e}")
            continue
    
    if not rows:
        log.warning(f"No buttons generated for node '{node_id}'")
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_keyboard_with_description(node_id: str, lang: str = "ru", **kwargs) -> tuple[str, InlineKeyboardMarkup]:
    """Построить текст и клавиатуру для узла меню"""
    node = get_menu_node(node_id)
    if not node:
        log.error(f"Menu node '{node_id}' not found")
        return "", InlineKeyboardMarkup(inline_keyboard=[])
    
    # Основной текст
    text_key = node.get("text_key", "menu.title")
    text = t(text_key, lang, **kwargs)
    
    # Описание (если есть)
    description_key = node.get("description_key")
    if description_key:
        description = t(description_key, lang, **kwargs)
        text = f"{text}\n\n{description}"
    
    keyboard = build_keyboard(node_id, lang, **kwargs)
    return text, keyboard

def get_menu_text(node_id: str, lang: str = "ru", **kwargs) -> str:
    """Получить текст для узла меню"""
    node = get_menu_node(node_id)
    if not node:
        return ""
    
    text_key = node.get("text_key", "menu.title")
    text = t(text_key, lang, **kwargs)
    
    description_key = node.get("description_key")
    if description_key:
        description = t(description_key, lang, **kwargs)
        text = f"{text}\n\n{description}"
    
    return text

# Специальные клавиатуры для обратной совместимости
def build_back_keyboard(target_node: str = "root", lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой "Назад" """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("btn.back", lang), 
            callback_data=Cb("nav", target_node).pack()
        )]
    ])

def build_home_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой "Главное меню" """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("btn.home", lang), 
            callback_data=Cb("nav", "root").pack()
        )]
    ])

def build_confirm_cancel_keyboard(action: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения/отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn.save", lang), 
                callback_data=Cb("confirm", action).pack()
            ),
            InlineKeyboardButton(
                text=t("btn.cancel", lang), 
                callback_data=Cb("cancel", action).pack()
            )
        ]
    ])

def build_retry_keyboard(action: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой повтора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn.retry", lang), 
                callback_data=Cb("retry", action).pack()
            ),
            InlineKeyboardButton(
                text=t("btn.back", lang), 
                callback_data=Cb("nav", "root").pack()
            )
        ]
    ])

# Утилиты для работы с существующими клавиатурами
def migrate_old_keyboard_to_schema(old_keyboard_func, node_id: str, lang: str = "ru"):
    """Миграция старой функции клавиатуры к новой схеме"""
    try:
        # Попробуем получить клавиатуру из схемы
        new_keyboard = build_keyboard(node_id, lang)
        if new_keyboard.inline_keyboard:
            return new_keyboard
    except Exception as e:
        log.warning(f"Failed to build new keyboard for {node_id}: {e}")
    
    # Fallback к старой функции
    try:
        return old_keyboard_func()
    except Exception as e:
        log.error(f"Failed to build old keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[])
