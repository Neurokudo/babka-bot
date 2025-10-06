# app/handlers/router.py
"""Единый роутер для обработки callback-ов и регистрация хэндлеров"""

from aiogram import types, Router
from app.ui.callbacks import parse_cb, Actions, Cb
from app.ui.keyboards import build_keyboard_with_description, build_home_keyboard
from app.ui.texts import t
from app.ui.legacy_mapping import convert_legacy_callback
import logging

log = logging.getLogger(__name__)

router = Router()
HANDLERS: dict[str, callable] = {}

def on_action(action: str):
    """Декоратор для регистрации хэндлера по действию"""
    def decorator(fn):
        HANDLERS[action] = fn
        log.info(f"Registered handler for action: {action}")
        return fn
    return decorator

@router.callback_query()
async def callback_entry(call: types.CallbackQuery):
    """Единая точка входа для всех callback-ов"""
    try:
        # Проверяем доступ (если функция доступна)
        # if not await check_access(call): return
        
        await call.answer()
        
        cb = parse_cb(call.data or "")
        
        # Если новый формат не распарсился, пробуем старый
        if not cb:
            legacy_cb = convert_legacy_callback(call.data)
            if legacy_cb:
                log.info(f"Converted legacy callback '{call.data}' to new format")
                cb = legacy_cb
            else:
                log.warning(f"Failed to parse callback data: '{call.data}'")
                await show_error_and_menu(call, "error.button_outdated")
                return
        
        if cb.action not in HANDLERS:
            log.warning(f"Unknown action: '{cb.action}' for callback: '{call.data}'")
            await show_error_and_menu(call, "error.button_outdated")
            return
        
        # Вызываем соответствующий хэндлер
        handler = HANDLERS[cb.action]
        await handler(call, cb)
        
    except Exception as e:
        log.error(f"Error in callback handler: {e}", exc_info=True)
        try:
            await show_error_and_menu(call, "error.button_outdated")
        except Exception:
            log.error("Failed to show error menu")

async def show_error_and_menu(call: types.CallbackQuery, error_key: str):
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
async def handle_nav(call: types.CallbackQuery, cb):
    """Навигация между экранами"""
    target = cb.id or "root"
    try:
        text, keyboard = build_keyboard_with_description(target)
        await call.message.edit_text(text, reply_markup=keyboard)
        log.info(f"Navigated to: {target}")
    except Exception as e:
        log.error(f"Navigation error to {target}: {e}")
        await show_error_and_menu(call, "error.button_outdated")

@on_action(Actions.HOME)
async def handle_home(call: types.CallbackQuery, cb):
    """Переход на главную страницу"""
    await handle_nav(call, cb)

@on_action(Actions.BACK)
async def handle_back(call: types.CallbackQuery, cb):
    """Кнопка "Назад" """
    target = cb.id or "root"
    await handle_nav(call, cb)

@on_action(Actions.CANCEL)
async def handle_cancel(call: types.CallbackQuery, cb):
    """Отмена действия"""
    await handle_nav(call, cb)

# === ГЛАВНОЕ МЕНЮ ===

@on_action(Actions.MENU_MAKE)
async def handle_menu_make(call: types.CallbackQuery, cb):
    """Переход к выбору режима генерации"""
    await handle_nav(call, cb)

@on_action(Actions.MENU_LEGO)
async def handle_menu_lego(call: types.CallbackQuery, cb):
    """Активация LEGO режима"""
    # Здесь можно добавить логику активации режима
    # st.update({"mode": "lego", "scene": None, "style": "LEGO", "replica": None})
    await handle_nav(call, cb)

@on_action(Actions.MENU_ALIVE)
async def handle_menu_alive(call: types.CallbackQuery, cb):
    """Оживление изображения (в разработке)"""
    await call.message.edit_text(
        t("menu.alive"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MENU_TRYON)
async def handle_menu_tryon(call: types.CallbackQuery, cb):
    """Виртуальная примерочная"""
    await handle_nav(call, cb)

@on_action(Actions.MENU_TRANSFORMS)
async def handle_menu_transforms(call: types.CallbackQuery, cb):
    """Трансформации изображений"""
    # Здесь можно добавить логику получения баланса пользователя
    # coins = st.get("coins", 0)
    # text = t("desc.transforms", coins=coins)
    await handle_nav(call, cb)

@on_action(Actions.MENU_JSONPRO)
async def handle_menu_jsonpro(call: types.CallbackQuery, cb):
    """JSON Pro режим"""
    await handle_nav(call, cb)

@on_action(Actions.MENU_GUIDES)
async def handle_menu_guides(call: types.CallbackQuery, cb):
    """Гайды и инструкции"""
    await call.message.edit_text(
        t("menu.guides"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MENU_PROFILE)
async def handle_menu_profile(call: types.CallbackQuery, cb):
    """Профиль пользователя"""
    await handle_nav(call, cb)

@on_action(Actions.MENU_HISTORY)
async def handle_menu_history(call: types.CallbackQuery, cb):
    """История генераций"""
    await call.message.edit_text(
        t("btn.history"),
        reply_markup=build_home_keyboard()
    )

# === РЕЖИМЫ ГЕНЕРАЦИИ ===

@on_action(Actions.MODE_HELPER)
async def handle_mode_helper(call: types.CallbackQuery, cb):
    """Режим с помощником"""
    await call.message.edit_text(
        t("mode.helper"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MODE_MANUAL)
async def handle_mode_manual(call: types.CallbackQuery, cb):
    """Ручной режим"""
    await call.message.edit_text(
        t("mode.manual"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MODE_MEME)
async def handle_mode_meme(call: types.CallbackQuery, cb):
    """Мем режим"""
    await call.message.edit_text(
        t("mode.meme"),
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MODE_NKUDO)
async def handle_mode_nkudo(call: types.CallbackQuery, cb):
    """НКУДО режим"""
    await handle_nav(call, cb)

@on_action(Actions.BACK_MODES)
async def handle_back_modes(call: types.CallbackQuery, cb):
    """Назад к режимам"""
    await handle_nav(call, cb)

# === LEGO РЕЖИМ ===

@on_action(Actions.LEGO_SINGLE)
async def handle_lego_single(call: types.CallbackQuery, cb):
    """LEGO одиночная сцена"""
    await handle_nav(call, cb)

@on_action(Actions.LEGO_REPORTAGE)
async def handle_lego_reportage(call: types.CallbackQuery, cb):
    """LEGO репортаж"""
    await handle_nav(call, cb)

@on_action(Actions.LEGO_REGENERATE)
async def handle_lego_regenerate(call: types.CallbackQuery, cb):
    """LEGO перегенерация"""
    await call.message.edit_text(
        "🔄 Перегенерирую LEGO сцену...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.LEGO_IMPROVE)
async def handle_lego_improve(call: types.CallbackQuery, cb):
    """LEGO улучшение"""
    await call.message.edit_text(
        "✨ Улучшаю LEGO сцену...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.LEGO_KEEP)
async def handle_lego_keep(call: types.CallbackQuery, cb):
    """LEGO оставить как есть"""
    await call.message.edit_text(
        "✅ LEGO сцена сохранена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.LEGO_CANCEL)
async def handle_lego_cancel(call: types.CallbackQuery, cb):
    """LEGO отмена"""
    await handle_nav(call, cb)

@on_action(Actions.LEGO_AGAIN)
async def handle_lego_again(call: types.CallbackQuery, cb):
    """LEGO еще раз"""
    await handle_lego_improve(call, cb)

@on_action(Actions.LEGO_EMBED_REPLICA)
async def handle_lego_embed_replica(call: types.CallbackQuery, cb):
    """LEGO встроить реплику"""
    await call.message.edit_text(
        "💬 Введите реплику для LEGO сцены:",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.LEGO_MENU_BACK)
async def handle_lego_menu_back(call: types.CallbackQuery, cb):
    """LEGO назад в меню"""
    await handle_nav(call, cb)

# === НКУДО РЕЖИМ ===

@on_action(Actions.NKUDO_SINGLE)
async def handle_nkudo_single(call: types.CallbackQuery, cb):
    """НКУДО одиночная сцена"""
    await handle_nav(call, cb)

@on_action(Actions.NKUDO_REPORTAGE)
async def handle_nkudo_reportage(call: types.CallbackQuery, cb):
    """НКУДО репортаж"""
    await handle_nav(call, cb)

@on_action(Actions.NKUDO_REGENERATE)
async def handle_nkudo_regenerate(call: types.CallbackQuery, cb):
    """НКУДО перегенерация"""
    await call.message.edit_text(
        "🔄 Перегенерирую НКУДО сцену...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_IMPROVE)
async def handle_nkudo_improve(call: types.CallbackQuery, cb):
    """НКУДО улучшение"""
    await call.message.edit_text(
        "✨ Улучшаю НКУДО сцену...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_KEEP)
async def handle_nkudo_keep(call: types.CallbackQuery, cb):
    """НКУДО оставить как есть"""
    await call.message.edit_text(
        "✅ НКУДО сцена сохранена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_CANCEL)
async def handle_nkudo_cancel(call: types.CallbackQuery, cb):
    """НКУДО отмена"""
    await handle_nav(call, cb)

@on_action(Actions.NKUDO_APPROVE)
async def handle_nkudo_approve(call: types.CallbackQuery, cb):
    """НКУДО одобрить"""
    await call.message.edit_text(
        "➡️ Переходим к генерации...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_REROLL_SCENE1)
async def handle_nkudo_reroll_scene1(call: types.CallbackQuery, cb):
    """НКУДО перекрутить сцену 1"""
    await call.message.edit_text(
        "🎲 Перекручиваю сцену 1...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_REROLL_SCENE2)
async def handle_nkudo_reroll_scene2(call: types.CallbackQuery, cb):
    """НКУДО перекрутить сцену 2"""
    await call.message.edit_text(
        "🎲 Перекручиваю сцену 2...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_EDIT_SCENE1)
async def handle_nkudo_edit_scene1(call: types.CallbackQuery, cb):
    """НКУДО редактировать сцену 1"""
    await call.message.edit_text(
        "✏️ Редактирую сцену 1...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_EDIT_SCENE2)
async def handle_nkudo_edit_scene2(call: types.CallbackQuery, cb):
    """НКУДО редактировать сцену 2"""
    await call.message.edit_text(
        "✏️ Редактирую сцену 2...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_REGENERATE_REPORT)
async def handle_nkudo_regenerate_report(call: types.CallbackQuery, cb):
    """НКУДО перегенерировать репортаж"""
    await call.message.edit_text(
        "🔄 Перегенерирую весь репортаж...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_IMPROVE_REPORT)
async def handle_nkudo_improve_report(call: types.CallbackQuery, cb):
    """НКУДО улучшить репортаж"""
    await call.message.edit_text(
        "🧠✨ Улучшаю репортаж помощником...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_EMBED_REPLICA)
async def handle_nkudo_embed_replica(call: types.CallbackQuery, cb):
    """НКУДО встроить реплику"""
    await call.message.edit_text(
        "💬 Введите реплику для НКУДО сцены:",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.NKUDO_MENU_BACK)
async def handle_nkudo_menu_back(call: types.CallbackQuery, cb):
    """НКУДО назад в меню"""
    await handle_nav(call, cb)

# === ТРАНСФОРМАЦИИ ===

@on_action(Actions.TRANSFORM_REMOVE_BG)
async def handle_transform_remove_bg(call: types.CallbackQuery, cb):
    """Удаление фона"""
    await call.message.edit_text(
        "✨ Удаляю фон...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_MERGE_PEOPLE)
async def handle_transform_merge_people(call: types.CallbackQuery, cb):
    """Совмещение людей"""
    await call.message.edit_text(
        "👥 Совмещаю людей...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_INJECT_OBJECT)
async def handle_transform_inject_object(call: types.CallbackQuery, cb):
    """Внедрение объекта"""
    await call.message.edit_text(
        "🧩 Внедряю объект...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_RETOUCH)
async def handle_transform_retouch(call: types.CallbackQuery, cb):
    """Магическая ретушь"""
    await call.message.edit_text(
        "🪄 Применяю магическую ретушь...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_POLAROID)
async def handle_transform_polaroid(call: types.CallbackQuery, cb):
    """Polaroid эффект"""
    await call.message.edit_text(
        "📷 Применяю Polaroid эффект...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_QUALITY_BASIC)
async def handle_transform_quality_basic(call: types.CallbackQuery, cb):
    """Базовая качество"""
    await call.message.edit_text(
        "⚡ Выбрано базовое качество",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_QUALITY_PREMIUM)
async def handle_transform_quality_premium(call: types.CallbackQuery, cb):
    """Премиум качество"""
    await call.message.edit_text(
        "💎 Выбрано премиум качество",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRANSFORM_RETRY)
async def handle_transform_retry(call: types.CallbackQuery, cb):
    """Повторить трансформацию"""
    await call.message.edit_text(
        "🔄 Повторяю трансформацию...",
        reply_markup=build_home_keyboard()
    )

# === ПРИМЕРОЧНАЯ ===

@on_action(Actions.TRYON_START)
async def handle_tryon_start(call: types.CallbackQuery, cb):
    """Начать примерку"""
    await handle_nav(call, cb)

@on_action(Actions.TRYON_SWAP)
async def handle_tryon_swap(call: types.CallbackQuery, cb):
    """Поменять местами"""
    await call.message.edit_text(
        "🔄 Меняю местами...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_RESET)
async def handle_tryon_reset(call: types.CallbackQuery, cb):
    """Сбросить примерку"""
    await call.message.edit_text(
        "🔄 Сбрасываю примерку...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_CONFIRM)
async def handle_tryon_confirm(call: types.CallbackQuery, cb):
    """Подтвердить примерку"""
    await call.message.edit_text(
        "✅ Примерка завершена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_NEW_POSE)
async def handle_tryon_new_pose(call: types.CallbackQuery, cb):
    """Новая поза"""
    await call.message.edit_text(
        "🔄 Генерирую новую позу...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_NEW_GARMENT)
async def handle_tryon_new_garment(call: types.CallbackQuery, cb):
    """Новая одежда"""
    await call.message.edit_text(
        "🔄 Меняю одежду...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_NEW_BG)
async def handle_tryon_new_bg(call: types.CallbackQuery, cb):
    """Новый фон"""
    await call.message.edit_text(
        "🔄 Меняю фон...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.TRYON_PROMPT)
async def handle_tryon_prompt(call: types.CallbackQuery, cb):
    """Улучшить промпт"""
    await call.message.edit_text(
        "💬 Введите улучшенный промпт:",
        reply_markup=build_home_keyboard()
    )

# === СТИЛИ ===

@on_action(Actions.STYLE_ANIME)
async def handle_style_anime(call: types.CallbackQuery, cb):
    """Стиль аниме"""
    await call.message.edit_text(
        "🇯🇵 Выбран стиль аниме",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.STYLE_LEGO)
async def handle_style_lego(call: types.CallbackQuery, cb):
    """Стиль LEGO"""
    await call.message.edit_text(
        "🧱 Выбран стиль LEGO",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.STYLE_NONE)
async def handle_style_none(call: types.CallbackQuery, cb):
    """Без стиля"""
    await call.message.edit_text(
        "⏩ Продолжаем без стиля",
        reply_markup=build_home_keyboard()
    )

# === ОРИЕНТАЦИЯ ===

@on_action(Actions.ORIENTATION_PORTRAIT)
async def handle_orientation_portrait(call: types.CallbackQuery, cb):
    """Портретная ориентация"""
    await call.message.edit_text(
        "📱 Выбрана портретная ориентация (9:16)",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ORIENTATION_LANDSCAPE)
async def handle_orientation_landscape(call: types.CallbackQuery, cb):
    """Альбомная ориентация"""
    await call.message.edit_text(
        "🖥️ Выбрана альбомная ориентация (16:9)",
        reply_markup=build_home_keyboard()
    )

# === JSON PRO ===

@on_action(Actions.JSONPRO_ENTER)
async def handle_jsonpro_enter(call: types.CallbackQuery, cb):
    """JSON Pro ввод"""
    await call.message.edit_text(
        "JSON Pro режим активирован",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.JSONPRO_ORI_916)
async def handle_jsonpro_ori_916(call: types.CallbackQuery, cb):
    """JSON Pro 9:16"""
    await call.message.edit_text(
        "📱 JSON Pro: портретная ориентация",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.JSONPRO_ORI_169)
async def handle_jsonpro_ori_169(call: types.CallbackQuery, cb):
    """JSON Pro 16:9"""
    await call.message.edit_text(
        "🖥️ JSON Pro: альбомная ориентация",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.JSONPRO_GENERATE)
async def handle_jsonpro_generate(call: types.CallbackQuery, cb):
    """JSON Pro генерация"""
    await call.message.edit_text(
        "🚀 JSON Pro генерация запущена",
        reply_markup=build_home_keyboard()
    )

# === ПЛАТЕЖИ И ТАРИФЫ ===

@on_action(Actions.PAYMENT_PLANS)
async def handle_payment_plans(call: types.CallbackQuery, cb):
    """Показать тарифы"""
    from app.services.pricing import format_plans_list, get_available_tariffs
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    import logging
    log = logging.getLogger(__name__)

    log.info("CALLBACK show_tariffs uid=%s", call.from_user.id)

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

# --- LEGACY SHIM: старые коллбеки на тарифы ---
@dp.callback_query_handler(lambda c: c.data in ("show_tariffs", "open_pricing"))
async def legacy_show_tariffs(call: types.CallbackQuery):
    """Legacy shim для старых коллбеков тарифов"""
    log.info("CALLBACK legacy_show_tariffs uid=%s data=%s", call.from_user.id, call.data)
    # используем актуальную реализацию
    try:
        return await handle_payment_plans(call, cb=None)
    except TypeError:
        # если сигнатура другая, просто вызовем без cb
        return await handle_payment_plans(call, None)

@on_action(Actions.PAYMENT_TOPUP)
async def handle_payment_topup(call: types.CallbackQuery, cb):
    """Пополнение баланса"""
    from app.services.pricing import format_topup_packs, get_available_topup_packs
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    log.info("CALLBACK show_topup uid=%s", call.from_user.id)

    topup_text = "💰 Пополнить монетки\n\n"
    topup_text += format_topup_packs()

    kb = []
    topup_packs = get_available_topup_packs()
    for pack in topup_packs:
        kb.append([InlineKeyboardButton(f"{pack['coins']} монет — {pack['price_rub']} ₽", callback_data=f"buy_topup_{pack['coins']}")])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_home")])

    await call.message.edit_text(topup_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

@on_action(Actions.PAYMENT_TERMS)
async def handle_payment_terms(call: types.CallbackQuery, cb):
    """Условия использования"""
    await call.message.edit_text(
        "📄 Условия использования",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.PAYMENT_SUPPORT)
async def handle_payment_support(call: types.CallbackQuery, cb):
    """Поддержка"""
    await call.message.edit_text(
        "💬 Служба поддержки",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.PAYMENT_CHANGE_PLAN)
async def handle_payment_change_plan(call: types.CallbackQuery, cb):
    """Смена тарифа"""
    await call.message.edit_text(
        "🔄 Смена тарифа",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.PAYMENT_SHOW_HISTORY)
async def handle_payment_show_history(call: types.CallbackQuery, cb):
    """История платежей"""
    await call.message.edit_text(
        "📜 История платежей",
        reply_markup=build_home_keyboard()
    )

# === СПЕЦИАЛЬНЫЕ ДЕЙСТВИЯ ===

@on_action(Actions.SCENE_SAVE)
async def handle_scene_save(call: types.CallbackQuery, cb):
    """Сохранить сцену"""
    await call.message.edit_text(
        "✅ Сцена сохранена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.SCENE_CANCEL)
async def handle_scene_cancel(call: types.CallbackQuery, cb):
    """Отменить сцену"""
    await call.message.edit_text(
        "❌ Сцена отменена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.SKIP_LOW_COINS)
async def handle_skip_low_coins(call: types.CallbackQuery, cb):
    """Пропустить предупреждение о низком балансе"""
    await handle_nav(call, cb)

@on_action(Actions.VIDEO_RETRY)
async def handle_video_retry(call: types.CallbackQuery, cb):
    """Повторить видео"""
    await call.message.edit_text(
        "🔄 Повторяю генерацию видео...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MEME_AGAIN)
async def handle_meme_again(call: types.CallbackQuery, cb):
    """Мем еще раз"""
    await call.message.edit_text(
        "😄 Генерирую новый мем...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.MEME_TO_HELPER)
async def handle_meme_to_helper(call: types.CallbackQuery, cb):
    """Мем с помощником"""
    await call.message.edit_text(
        "🤖 Мем с помощником...",
        reply_markup=build_home_keyboard()
    )

# === ДОПОЛНИТЕЛЬНЫЕ ДЕЙСТВИЯ ===

@on_action(Actions.ACTION_ADD_PROMPT)
async def handle_action_add_prompt(call: types.CallbackQuery, cb):
    """Добавить промпт"""
    await call.message.edit_text(
        "➕ Добавьте промпт:",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_EDIT_REPLICA)
async def handle_action_edit_replica(call: types.CallbackQuery, cb):
    """Редактировать реплику"""
    await call.message.edit_text(
        "✏️ Редактируйте реплику:",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_BACK_FINAL)
async def handle_action_back_final(call: types.CallbackQuery, cb):
    """Назад к финалу"""
    await handle_nav(call, cb)

@on_action(Actions.ACTION_GENERATE_REPLICA)
async def handle_action_generate_replica(call: types.CallbackQuery, cb):
    """Генерировать реплику"""
    await call.message.edit_text(
        "🚀 Генерирую реплику...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_GENERATE_FINAL)
async def handle_action_generate_final(call: types.CallbackQuery, cb):
    """Генерировать финал"""
    await call.message.edit_text(
        "🚀 Генерирую финал...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_MANUAL_REPLICA)
async def handle_action_manual_replica(call: types.CallbackQuery, cb):
    """Ввести реплику вручную"""
    await call.message.edit_text(
        "✏️ Введите реплику вручную:",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_CANCEL_MANUAL)
async def handle_action_cancel_manual(call: types.CallbackQuery, cb):
    """Отменить ручной ввод"""
    await call.message.edit_text(
        "❌ Ручной ввод отменен",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_VAR_COMPLEX)
async def handle_action_var_complex(call: types.CallbackQuery, cb):
    """Сложный вариант"""
    await call.message.edit_text(
        "🎭 Генерирую сложный вариант...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_VAR_SIMPLE)
async def handle_action_var_simple(call: types.CallbackQuery, cb):
    """Простой вариант"""
    await call.message.edit_text(
        "😊 Генерирую простой вариант...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_VAR_AGAIN)
async def handle_action_var_again(call: types.CallbackQuery, cb):
    """Другой вариант"""
    await call.message.edit_text(
        "🔄 Генерирую другой вариант...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_PHRASE)
async def handle_action_phrase(call: types.CallbackQuery, cb):
    """Придумать фразу"""
    await call.message.edit_text(
        "💬 Придумываю фразу...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_AUDIO_YES)
async def handle_action_audio_yes(call: types.CallbackQuery, cb):
    """С музыкой"""
    await call.message.edit_text(
        "🎵 Генерирую с музыкой...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_AUDIO_NO)
async def handle_action_audio_no(call: types.CallbackQuery, cb):
    """Без музыки"""
    await call.message.edit_text(
        "🔇 Генерирую без музыки...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_CANCEL_PROCEDURE)
async def handle_action_cancel_procedure(call: types.CallbackQuery, cb):
    """Отменить процедуру"""
    await call.message.edit_text(
        "❌ Процедура отменена",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_EDIT_FROM_LAST)
async def handle_action_edit_from_last(call: types.CallbackQuery, cb):
    """Редактировать последнее"""
    await call.message.edit_text(
        "✏️ Редактирую последнее...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.ACTION_REFINE_PROMPT)
async def handle_action_refine_prompt(call: types.CallbackQuery, cb):
    """Улучшить промпт"""
    await call.message.edit_text(
        "✨ Улучшаю промпт...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.GENERATE_NOW)
async def handle_generate_now(call: types.CallbackQuery, cb):
    """Генерировать сейчас"""
    await call.message.edit_text(
        "🚀 Генерация запущена...",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.GO_ORIENTATION)
async def handle_go_orientation(call: types.CallbackQuery, cb):
    """Перейти к выбору ориентации"""
    await handle_nav(call, cb)

# === УЛУЧШЕНИЯ ===

@on_action(Actions.IMPROVE_KEEP)
async def handle_improve_keep(call: types.CallbackQuery, cb):
    """Оставить улучшение"""
    await call.message.edit_text(
        "✅ Улучшение сохранено",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.IMPROVE_CANCEL)
async def handle_improve_cancel(call: types.CallbackQuery, cb):
    """Отменить улучшение"""
    await call.message.edit_text(
        "❌ Улучшение отменено",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.REPORT_IMPROVE_KEEP)
async def handle_report_improve_keep(call: types.CallbackQuery, cb):
    """Оставить улучшение репортажа"""
    await call.message.edit_text(
        "✅ Улучшение репортажа сохранено",
        reply_markup=build_home_keyboard()
    )

@on_action(Actions.REPORT_IMPROVE_CANCEL)
async def handle_report_improve_cancel(call: types.CallbackQuery, cb):
    """Отменить улучшение репортажа"""
    await call.message.edit_text(
        "❌ Улучшение репортажа отменено",
        reply_markup=build_home_keyboard()
    )

# Функция для регистрации роутера в основном боте
def register_router(dispatcher):
    """Зарегистрировать роутер в диспетчере"""
    dispatcher.add_handler(router)
    log.info("Callback router registered")

# Функция для получения списка зарегистрированных хэндлеров
def get_registered_handlers():
    """Получить список зарегистрированных хэндлеров"""
    return list(HANDLERS.keys())
