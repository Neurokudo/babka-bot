# app/handlers/router_v2.py
"""Единый роутер для обработки callback-ов и регистрация хэндлеров для python-telegram-bot"""

from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from app.ui.callbacks import parse_cb, Actions, Cb
from app.ui.keyboards import build_keyboard_with_description, build_home_keyboard
from app.ui.texts import t
from app.ui.legacy_mapping import convert_legacy_callback
import logging

log = logging.getLogger(__name__)

HANDLERS: dict[str, callable] = {}

def on_action(action: str):
    """Декоратор для регистрации хэндлера по действию"""
    def decorator(fn):
        HANDLERS[action] = fn
        log.info(f"Registered handler for action: {action}")
        return fn
    return decorator

async def callback_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единая точка входа для всех callback-ов"""
    try:
        call = update.callback_query
        if not call:
            return
            
        # Проверяем доступ (если функция доступна)
        # if not await check_access(call): return
        
        await call.answer()
        
        log.info(f"🔍 ROUTER CALLBACK: '{call.data}' from uid={call.from_user.id}")
        cb = parse_cb(call.data or "")
        
        # Если новый формат не распарсился, пробуем старый
        if not cb:
            log.info(f"Trying legacy conversion for callback: '{call.data}'")
            legacy_cb = convert_legacy_callback(call.data)
            if legacy_cb:
                log.info(f"✅ Converted legacy callback '{call.data}' to new format: {legacy_cb}")
                cb = legacy_cb
            else:
                log.warning(f"❌ Failed to parse callback data: '{call.data}'")
                await show_error_and_menu(call, "error.button_outdated")
                return
        
        if cb.action not in HANDLERS:
            log.warning(f"Unknown action: '{cb.action}' for callback: '{call.data}'")
            log.warning(f"Available handlers: {list(HANDLERS.keys())}")
            await show_error_and_menu(call, "error.button_outdated")
            return
        
        # Вызываем соответствующий хэндлер
        handler = HANDLERS[cb.action]
        await handler(update, context, cb)
        
    except Exception as e:
        log.error(f"Error in callback handler: {e}", exc_info=True)
        try:
            await show_error_and_menu(call, "error.button_outdated")
        except Exception:
            log.error("Failed to show error menu")

async def show_error_and_menu(call: CallbackQuery, error_key: str):
    """Показать ошибку и главное меню"""
    try:
        error_text = t(error_key)
        text, keyboard = build_keyboard_with_description("root")
        
        await call.message.edit_text(
            f"{error_text}\n\n{text}",
            reply_markup=keyboard
        )
    except Exception as e:
        log.error(f"Failed to show error menu: {e}")
        # Последняя попытка - показать только главное меню
        try:
            text, keyboard = build_keyboard_with_description("root")
            await call.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            log.error("Complete failure to show menu")

# === НАВИГАЦИОННЫЕ ХЭНДЛЕРЫ ===

@on_action(Actions.NAV)
async def handle_nav(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Навигация между экранами"""
    call = update.callback_query
    target = cb.id or "root"
    try:
        text, keyboard = build_keyboard_with_description(target)
        await call.message.edit_text(text, reply_markup=keyboard)
        log.info(f"Navigated to: {target}")
    except Exception as e:
        log.error(f"Navigation error to {target}: {e}")
        await show_error_and_menu(call, "error.button_outdated")

@on_action(Actions.HOME)
async def handle_home(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Переход на главную страницу"""
    await handle_nav(update, context, cb)

@on_action(Actions.BACK)
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Кнопка "Назад" """
    await handle_nav(update, context, cb)

@on_action(Actions.CANCEL)
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Отмена действия"""
    await handle_nav(update, context, cb)

# === ГЛАВНОЕ МЕНЮ ===

@on_action(Actions.MENU_MAKE)
async def handle_menu_make(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Переход к выбору режима генерации"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_LEGO)
async def handle_menu_lego(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Активация LEGO режима"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_ALIVE)
async def handle_menu_alive(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Оживление изображения (в разработке)"""
    call = update.callback_query
    await call.message.edit_text(
        t("menu.alive"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MENU_TRYON)
async def handle_menu_tryon(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Виртуальная примерочная"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_TRANSFORMS)
async def handle_menu_transforms(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Трансформации изображений"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_JSONPRO)
async def handle_menu_jsonpro(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """JSON Pro режим"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_GUIDES)
async def handle_menu_guides(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Гайды и инструкции"""
    call = update.callback_query
    await call.message.edit_text(
        t("menu.guides"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MENU_PROFILE)
async def handle_menu_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Профиль пользователя"""
    await handle_nav(update, context, cb)

@on_action(Actions.MENU_HISTORY)
async def handle_menu_history(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """История генераций"""
    call = update.callback_query
    await call.message.edit_text(
        t("btn.history"),
        reply_markup=build_home_keyboard()
    )

# === ПЛАТЕЖИ И ТАРИФЫ ===

@on_action(Actions.PAYMENT_PLANS)
async def handle_payment_plans(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Показать тарифы"""
    call = update.callback_query
    from app.services.pricing import format_plans_list, get_available_tariffs
    import logging
    log = logging.getLogger(__name__)

    log.info("CALLBACK handle_payment_plans uid=%s", call.from_user.id)

    # Безопасная сборка текста
    try:
        plans_text = format_plans_list()
    except Exception as e:
        log.error("Failed to build plans list: %s", e, exc_info=True)
        plans_text = "❌ Ошибка при загрузке тарифов. Попробуйте ещё раз."

    # Диагностический бейдж версии (оставить, если в проекте есть эти переменные)
    try:
        from main import VERSION, PRICING_HASH
        plans_text += f"\n\n🧩 version: {VERSION} • pricing: {PRICING_HASH}"
    except Exception:
        pass

    # Клавиатура на основе списка (не dict!)
    kb = []
    try:
        tariffs = get_available_tariffs()  # ожидается list[dict]
        for info in tariffs:
            key = info["name"]
            title = info["title"]
            price = info["price_rub"]
            kb.append([InlineKeyboardButton(f"{title} — {price:,} ₽", callback_data=f"buy_plan_{key}")])
    except Exception as e:
        log.error("Failed to build tariffs keyboard: %s", e, exc_info=True)

    kb.append([InlineKeyboardButton("➕ Пополнить монеты", callback_data="show_topup")])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_home")])

    await call.message.edit_text(plans_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

@on_action(Actions.PAYMENT_TOPUP)
async def handle_payment_topup(update: Update, context: ContextTypes.DEFAULT_TYPE, cb):
    """Пополнение баланса"""
    call = update.callback_query
    from app.services.pricing import format_topup_packs, get_available_topup_packs

    log.info("CALLBACK show_topup uid=%s", call.from_user.id)

    topup_text = "💰 Пополнить монетки\n\n"
    topup_text += format_topup_packs()

    kb = []
    topup_packs = get_available_topup_packs()
    for pack in topup_packs:
        kb.append([InlineKeyboardButton(f"{pack['coins']} монет — {pack['price_rub']} ₽", callback_data=f"buy_topup_{pack['coins']}")])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_home")])

    await call.message.edit_text(topup_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

# Функция для регистрации роутера в основном боте
def register_router(app):
    """Зарегистрировать роутер в приложении"""
    app.add_handler(CallbackQueryHandler(callback_entry))
    log.info("✅ Callback router registered successfully")
    log.info(f"📋 Registered handlers: {list(HANDLERS.keys())}")
    print(f"🔧 ROUTER INIT: Registered {len(HANDLERS)} handlers")

# Функция для получения списка зарегистрированных хэндлеров
def get_registered_handlers():
    """Получить список зарегистрированных хэндлеров"""
    return list(HANDLERS.keys())
