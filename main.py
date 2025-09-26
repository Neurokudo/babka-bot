import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ──────────────────────────────────────────────────────────────
# .env — локально; на Railway переменные берутся из Variables
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# Логи
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

# ──────────────────────────────────────────────────────────────
# Состояние пользователя
user_state: dict[int, dict] = {}
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "Кино")

def _ensure_state(uid: int):
    if uid not in user_state:
        user_state[uid] = {
            "mode": None,
            "prompt": None,
            "style": None,
            "replica": None,
            "awaiting_prompt": False,
            "awaiting_replica": False,
            "awaiting_custom_style": False,
        }

# ──────────────────────────────────────────────
# Gemini (google-generativeai==0.8.5)
import google.generativeai as genai

_GEMINI_CANDIDATES = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
]

gemini_model = None
if os.getenv("LLM_PROVIDER", "").lower() == "gemini" and os.getenv("GOOGLE_API_KEY"):
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        last_err = None
        for mid in _GEMINI_CANDIDATES:
            try:
                gemini_model = genai.GenerativeModel(mid)
                log.info("Gemini enabled. Using model: %s", mid)
                break
            except Exception as e:
                last_err = e
                log.warning("Gemini model '%s' failed: %s", mid, e)
        if not gemini_model:
            raise last_err or RuntimeError("No Gemini model available")
    except Exception as e:
        gemini_model = None
        log.error("Gemini init failed: %s", e)
else:
    log.info("Gemini disabled (LLM_PROVIDER != gemini or GOOGLE_API_KEY missing)")

def _gemini_text(prompt: str, *, temperature: float = 0.8, max_tokens: int = 256) -> Optional[str]:
    if not gemini_model:
        return None
    try:
        resp = gemini_model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "top_p": 0.95, "max_output_tokens": max_tokens},
        )
        text = (getattr(resp, "text", "") or "").strip()
        return text or None
    except Exception as e:
        log.error("Gemini error: %s", e)
        return None

def improve_prompt(user_text: str) -> tuple[str, bool]:
    sys = (
        "Ты редактор промтов для генерации КОРОТКИХ видеосцен. "
        "Верни 1–2 предложения без кавычек и списков. "
        "Добавь детали камеры/света/движения/настроения. "
        "Запрещено: любой текст/водяные знаки в кадре."
    )
    out = _gemini_text(f"{sys}\nИсходный текст сцены: {user_text}", temperature=0.7, max_tokens=120)
    return (out, True) if out else (user_text, False)

def suggest_replica(prompt: str) -> Optional[str]:
    sys = (
        "Придумай ОДНУ короткую реплику персонажа (4–10 слов) под следующую сцену. "
        "Только сама фраза, без кавычек и комментариев."
    )
    return _gemini_text(f"{sys}\nСцена: {prompt}", temperature=0.9, max_tokens=40)

# ──────────────────────────────────────────────
# Veo клиент
from veo_client import generate_video_sync

# ──────────────────────────────────────────────
# Клавиатуры
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео с помощником", callback_data="menu_make")],
        [InlineKeyboardButton("🖼️ Оживление изображения", callback_data="menu_alive")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
        [InlineKeyboardButton("⚙️ Профиль / Баланс", callback_data="menu_profile")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="mode_helper")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_main")],
    ])

def kb_after_prompt():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Выбрать стиль", callback_data="choose_style")],
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="replica_menu")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="back_modes")],
    ])

def kb_style_list():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Кино", callback_data="style_Кино"),
         InlineKeyboardButton("📺 Док", callback_data="style_Док")],
        [InlineKeyboardButton("🎨 Анимация", callback_data="style_Анимация"),
         InlineKeyboardButton("✏️ Ввести свой стиль", callback_data="style_custom")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_after_prompt")],
    ])

def kb_replica_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Введу сам текст", callback_data="replica_custom")],
        [InlineKeyboardButton("🤖 Пусть бот предложит", callback_data="replica_ai")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_after_prompt")],
    ])

# ──────────────────────────────────────────────
# Хэндлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure_state(uid)
    user_state[uid].update({
        "mode": None, "prompt": None, "style": None, "replica": None,
        "awaiting_prompt": False, "awaiting_replica": False, "awaiting_custom_style": False,
    })
    await update.message.reply_text("👋 Привет! Я бот для генерации видео.", reply_markup=kb_main())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure_state(uid)
    st = user_state[uid]
    text = update.message.text.strip()

    # ждём кастомный стиль
    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"🎨 Стиль сохранён: {text}", reply_markup=kb_after_prompt())
        return

    # ждём ручную реплику
    if st["awaiting_replica"]:
        st["awaiting_replica"] = False
        st["replica"] = text
        await update.message.reply_text(f"💬 Реплика сохранена: {text}", reply_markup=kb_after_prompt())
        return

    # ждём промт
    if st["awaiting_prompt"]:
        st["awaiting_prompt"] = False
        if st["mode"] == "helper" and gemini_model:
            improved, ok = improve_prompt(text)
            st["prompt"] = improved
            if ok:
                await update.message.reply_text(
                    f"📝 Промт улучшен:\n\n{improved}",
                    reply_markup=kb_after_prompt()
                )
            else:
                await update.message.reply_text(
                    "⚠️ Gemini сейчас недоступен. Сохраняю промт без изменений:\n\n" + improved,
                    reply_markup=kb_after_prompt()
                )
        else:
            st["prompt"] = text
            await update.message.reply_text(
                f"📝 Промт сохранён:\n\n{text}",
                reply_markup=kb_after_prompt()
            )
        return

    # если ничего не ждём — показать меню
    await update.message.reply_text("Выбери действие:", reply_markup=kb_main())

# (button_handler и main без изменений, оставь их как у тебя)

