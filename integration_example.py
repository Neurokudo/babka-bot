#!/usr/bin/env python3
# integration_example.py
"""Пример интеграции новой UI системы в main.py"""

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.handlers.router import register_router
from app.ui.keyboards import build_keyboard_with_description
from app.ui.texts import t

# Пример функции для замены существующей on_cb
async def new_on_cb(update, context):
    """Новый обработчик callback-ов через роутер"""
    # Проверяем доступ (если функция доступна)
    # if not await check_access(update): return
    
    try:
        # Используем новый роутер
        from app.handlers.router import callback_entry
        await callback_entry(update.callback_query)
    except Exception as e:
        print(f"Error in new callback handler: {e}")
        # Fallback к старому обработчику
        await old_on_cb(update, context)

# Пример функции для создания приложения с новой системой
def create_app_with_new_ui():
    """Создание приложения с новой UI системой"""
    
    # Создаем приложение
    app = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # Регистрируем команды (без изменений)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whereami", cmd_whereami))
    app.add_handler(CommandHandler("terms", cmd_terms))
    # ... остальные команды
    
    # ЗАМЕНЯЕМ старый CallbackQueryHandler на новый
    # app.add_handler(CallbackQueryHandler(on_cb))  # СТАРЫЙ
    app.add_handler(CallbackQueryHandler(new_on_cb))  # НОВЫЙ
    
    # Или можно использовать роутер напрямую:
    # register_router(app)  # Это заменит все callback обработчики
    
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    
    return app

# Пример функции для замены старых клавиатур
def create_home_keyboard_new():
    """Создание главного меню через новую систему"""
    text, keyboard = build_keyboard_with_description("root")
    return text, keyboard

# Пример функции для замены старых callback-ов
def create_callback_new(action, node_id=None, extra=None):
    """Создание callback данных через новую систему"""
    from app.ui.callbacks import Cb
    return Cb(action, node_id, extra).pack()

# Пример миграции старой функции клавиатуры
def migrate_kb_home_inline():
    """Миграция старой kb_home_inline() к новой системе"""
    # СТАРЫЙ КОД:
    # def kb_home_inline():
    #     return InlineKeyboardMarkup([
    #         [InlineKeyboardButton("🎬 Генерировать видео", callback_data="menu_make")],
    #         [InlineKeyboardButton("🧱 LEGO мультики", callback_data="menu_lego")],
    #         [InlineKeyboardButton("🖼️ Оживить фото", callback_data="menu_alive")],
    #         [InlineKeyboardButton("👗 Примерочная", callback_data="menu_tryon")],
    #         [InlineKeyboardButton("📸 Изменить фото", callback_data="menu_transforms")],
    #         [InlineKeyboardButton("⚡ JSON Pro", callback_data="menu_jsonpro")],
    #         [InlineKeyboardButton("📚 Гайды", callback_data="menu_guides")],
    #         [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
    #         [InlineKeyboardButton("📜 История", callback_data="show_history")],
    #     ])
    
    # НОВЫЙ КОД:
    text, keyboard = build_keyboard_with_description("root")
    return keyboard

# Пример замены старого callback обработчика
async def old_on_cb(update, context):
    """Старый обработчик callback-ов (для fallback)"""
    # Здесь будет код из существующей функции on_cb
    pass

# Пример команды с новой системой
async def cmd_start_new(update, context):
    """Новая версия команды /start"""
    text, keyboard = build_keyboard_with_description("root")
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Пример функции для постепенной миграции
def create_migration_wrapper(old_callback_func):
    """Создание обертки для постепенной миграции"""
    async def wrapper(update, context):
        try:
            # Сначала пробуем новый роутер
            from app.handlers.router import callback_entry
            await callback_entry(update.callback_query)
        except Exception as e:
            print(f"New router failed, falling back to old handler: {e}")
            # Fallback к старому обработчику
            await old_callback_func(update, context)
    
    return wrapper

# Пример использования миграционной обертки
def setup_migrated_app():
    """Настройка приложения с миграционной оберткой"""
    app = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # Используем миграционную обертку
    migrated_callback_handler = create_migration_wrapper(old_on_cb)
    app.add_handler(CallbackQueryHandler(migrated_callback_handler))
    
    return app

if __name__ == "__main__":
    print("Этот файл содержит примеры интеграции новой UI системы.")
    print("Скопируйте нужные функции в main.py для миграции.")
