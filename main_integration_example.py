#!/usr/bin/env python3
# main_integration_example.py
"""Пример интеграции новой UI системы в main.py"""

# Добавьте эти импорты в начало main.py
from app.handlers.router import register_router, callback_entry
from app.ui.keyboards import build_keyboard_with_description
from app.ui.texts import t

# Пример замены функции create_app()
def create_app_with_new_ui():
    """Создание Telegram Application с новой UI системой"""
    if not BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
    
    # Проверяем просроченные подписки при старте
    check_and_reset_expired_plans()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды (без изменений)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whereami", cmd_whereami))
    app.add_handler(CommandHandler("terms", cmd_terms))
    app.add_handler(CommandHandler("sync_pricing", lambda u, c: u.message.reply_text(pricing_text(), parse_mode="HTML")))
    app.add_handler(CommandHandler("test_payment", cmd_test_payment))
    app.add_handler(CommandHandler("add_bonus", cmd_add_bonus))
    app.add_handler(CommandHandler("reload_profile", cmd_reload_profile))
    app.add_handler(CommandHandler("reset_my_profile", cmd_reset_my_profile))
    
    # ЗАМЕНА: старый CallbackQueryHandler на новый роутер
    # app.add_handler(CallbackQueryHandler(on_cb))  # СТАРЫЙ
    register_router(app)  # НОВЫЙ - это заменит все callback обработчики
    
    # Остальные обработчики (без изменений)
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    
    return app

# Пример замены функции kb_home_inline()
def kb_home_inline_new():
    """Новая версия главного меню"""
    # СТАРЫЙ КОД:
    # return InlineKeyboardMarkup([
    #     [InlineKeyboardButton("🎬 Генерировать видео", callback_data="menu_make")],
    #     [InlineKeyboardButton("🧱 LEGO мультики", callback_data="menu_lego")],
    #     [InlineKeyboardButton("🖼️ Оживить фото", callback_data="menu_alive")],
    #     [InlineKeyboardButton("👗 Примерочная", callback_data="menu_tryon")],
    #     [InlineKeyboardButton("📸 Изменить фото", callback_data="menu_transforms")],
    #     [InlineKeyboardButton("⚡ JSON Pro", callback_data="menu_jsonpro")],
    #     [InlineKeyboardButton("📚 Гайды", callback_data="menu_guides")],
    #     [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
    #     [InlineKeyboardButton("📜 История", callback_data="show_history")],
    # ])
    
    # НОВЫЙ КОД:
    _, keyboard = build_keyboard_with_description("root")
    return keyboard

# Пример замены команды /start
async def cmd_start_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Новая версия команды /start"""
    uid = update.effective_user.id
    _ensure(uid)
    
    # СТАРЫЙ КОД:
    # await update.message.reply_text(
    #     "🏠 Главное меню",
    #     reply_markup=kb_home_inline(),
    #     parse_mode="HTML"
    # )
    
    # НОВЫЙ КОД:
    text, keyboard = build_keyboard_with_description("root")
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Пример замены команды /coins
async def cmd_coins_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Новая версия команды /coins"""
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    
    # СТАРЫЙ КОД:
    # await update.message.reply_text(
    #     "💰 <b>Пополнить баланс</b>\n\n"
    #     "Выберите способ пополнения:",
    #     parse_mode="HTML",
    #     reply_markup=InlineKeyboardMarkup([
    #         [InlineKeyboardButton("📋 Тарифы", callback_data="show_plans")],
    #         [InlineKeyboardButton("💰 Монетки", callback_data="show_topup")],
    #         [InlineKeyboardButton("🏠 Главное меню", callback_data="back_home")],
    #     ])
    # )
    
    # НОВЫЙ КОД:
    text, keyboard = build_keyboard_with_description("profile")
    await update.message.reply_text(
        "💰 <b>Пополнить баланс</b>\n\nВыберите способ пополнения:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# Пример миграционной обертки для постепенного перехода
async def migrated_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Миграционная обертка для callback-ов"""
    try:
        # Сначала пробуем новый роутер
        await callback_entry(update.callback_query)
    except Exception as e:
        log.error(f"New callback router failed: {e}")
        # Fallback к старому обработчику
        await on_cb(update, context)

# Пример использования миграционной обертки в create_app()
def create_app_with_migration():
    """Создание приложения с миграционной оберткой"""
    if not BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
    
    check_and_reset_expired_plans()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", cmd_start_new))  # Используем новую версию
    app.add_handler(CommandHandler("coins", cmd_coins_new))  # Используем новую версию
    # ... остальные команды
    
    # Используем миграционную обертку
    app.add_handler(CallbackQueryHandler(migrated_callback_handler))
    
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    
    return app

# Пример замены других функций клавиатур
def kb_modes_new():
    """Новая версия клавиатуры режимов"""
    return build_keyboard_with_description("modes")[1]  # Возвращаем только клавиатуру

def kb_lego_menu_new():
    """Новая версия клавиатуры LEGO меню"""
    return build_keyboard_with_description("lego_menu")[1]

def kb_nkudo_menu_new():
    """Новая версия клавиатуры НКУДО меню"""
    return build_keyboard_with_description("nkudo_menu")[1]

def kb_transforms_new():
    """Новая версия клавиатуры трансформаций"""
    return build_keyboard_with_description("transforms")[1]

def kb_profile_new():
    """Новая версия клавиатуры профиля"""
    return build_keyboard_with_description("profile")[1]

# Пример функции для замены текстов в существующих функциях
def get_menu_text_new(menu_type: str) -> str:
    """Получить текст меню через новую систему"""
    text_map = {
        "home": "menu.title",
        "modes": "menu.generate",
        "lego": "menu.lego",
        "transforms": "menu.transforms",
        "profile": "menu.profile",
        "tryon": "menu.tryon",
        "jsonpro": "menu.jsonpro",
    }
    
    text_key = text_map.get(menu_type, "menu.title")
    return t(text_key)

# Пример замены создания callback данных
def create_callback_new(action: str, node_id: str = None, extra: str = None) -> str:
    """Создать callback данные через новую систему"""
    from app.ui.callbacks import Cb
    return Cb(action, node_id, extra).pack()

# Пример замены в существующих функциях
async def example_usage_in_existing_function():
    """Пример использования новой системы в существующих функциях"""
    
    # Вместо:
    # await message.reply_text("Выберите режим:", reply_markup=kb_modes())
    
    # Используйте:
    text, keyboard = build_keyboard_with_description("modes")
    await message.reply_text(text, reply_markup=keyboard)
    
    # Или для создания callback данных:
    callback_data = create_callback_new("nav", "lego_menu")
    
    # Или для получения текста:
    menu_text = get_menu_text_new("lego")

if __name__ == "__main__":
    print("Этот файл содержит примеры интеграции новой UI системы в main.py")
    print("Скопируйте нужные функции и замените соответствующие части в main.py")
    print("Для полной миграции используйте create_app_with_new_ui()")
    print("Для постепенной миграции используйте create_app_with_migration()")
