# main.py
import os
import logging
import random
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

# ──────────────────────────────────────────────────────────────────────────────
# Загружаем .env локально; на Railway всё берётся из Variables
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# Логи
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

# Глобальное состояние
user_state: dict[int, dict] = {}
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "cinema")

def _ensure_state(uid: int):
    if uid not in user_state:
        user_state[uid] = {
            "mode": None,                   # helper | manual | meme
            "prompt": None,                 # текущий промт
            "style": None,                  # выбранный стиль
            "replica": None,                # текст реплики
            "awaiting_replica": False,      # ждём ручной ввод реплики
            "awaiting_custom_style": False, # ждём ручной ввод стиля
        }

# ──────────────────────────────────────────────────────────────────────────────
# Gemini (google-generativeai==0.8.5)
import google.generativeai as genai

GENAI_MODEL = os.getenv("GENAI_MODEL", "").strip()
_GEMINI_CANDIDATES = [m for m in [
    GENAI_MODEL or None,
    "gemini-1.5-flash",   # основной
    "gemini-1.5-pro",     # продвинутая
] if m]

GEMINI_ENABLED = os.getenv("LLM_PROVIDER") == "gemini" and bool(os.getenv("GOOGLE_API_KEY"))
gemini_model = None
if GEMINI_ENABLED:
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
    log.info("Gemini disabled (LLM_PROVIDER != gemini or GOOGLE_API_KEY is empty).")

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
        log.exception("Gemini error: %s", e)
        return None

def improve_prompt(user_text: str) -> str:
    sys = (
        "Ты редактор промтов для генерации видео. "
        "На выходе дай 1–2 предложения, без списков, без кавычек, без хэштегов. "
        "Добавь детали: свет, камера, действие, настроение. Никакого текста на экране."
    )
    out = _gemini_text(f"{sys}\nИсходный текст: {user_text}", temperature=0.7, max_tokens=120)
    return out or user_text

def suggest_replica(prompt: str) -> str:
    sys = "Придумай короткую живую смешную реплику к этому промту. Только одну."
    out = _gemini_text(f"{sys}\nПромт: {prompt}", temperature=0.9, max_tokens=40)
    return out or "Ну держитесь теперь!"

# ──────────────────────────────────────────────────────────────────────────────
# Клавиатуры
def kb_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео с помощником", callback_data="menu_create")],
        [InlineKeyboardButton("🖼️ Оживление изображения", callback_data="menu_image")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
        [InlineKeyboardButton("⚙️ Профиль / Баланс", callback_data="menu_profile")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="helper")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="meme_mode")],
    ])

def kb_after_prompt():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ К стилям", callback_data="prompt_to_styles")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")],
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="choose_replica")],
    ])

def kb_replica_options():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Я сам напишу", callback_data="replica_manual")],
        [InlineKeyboardButton("🤖 Пусть бот предложит", callback_data="replica_ai")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="replica_back")],
    ])

def kb_styles():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Кино", callback_data="style_cinema")],
        [InlineKeyboardButton("🎧 ASMR", callback_data="style_asmr")],
        [InlineKeyboardButton("🏢 Бренд", callback_data="style_brand")],
        [InlineKeyboardButton("🎥 Документальный", callback_data="style_doc")],
        [InlineKeyboardButton("🎨 Арт / Ретро / ЧБ", callback_data="style_art")],
        [InlineKeyboardButton("🤖 Киберпанк", callback_data="style_cyber")],
        [InlineKeyboardButton("✨ Pixar", callback_data="style_pixar")],
        [InlineKeyboardButton("➕ Предложить ещё стиль", callback_data="style_more")],
        [InlineKeyboardButton("🚀 Сгенерировать без стиля", callback_data="style_skip_generate")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="style_back")],
    ])

# ──────────────────────────────────────────────────────────────────────────────
# Мемные промты
def generate_meme_prompt():
    subjects = ["Бабка","Дед","Гламурная девица","Неформал","Рокер","Строитель","Слон","Носорог","Бегемот","Капибара"]
    actions = ["едет верхом","падает","кричит","танцует","спорит","машет руками"]
    objects = ["на свинье","с самоваром","рядом с холодильником","с портретом Ленина"]
    locations = ["в деревне","в панельном районе","на стадионе","у бассейна","на стройке"]
    return f"{random.choice(subjects)} {random.choice(actions)} {random.choice(objects)} {random.choice(locations)}"

# ──────────────────────────────────────────────────────────────────────────────
# Хэндлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_state(update.effective_user.id)
    await update.message.reply_text("👋 Привет! Я бот для генерации видео.", reply_markup=kb_main_menu())

# TODO: сюда подключить остальной код обработки кнопок и генерации видео
# ...

# ──────────────────────────────────────────────────────────────────────────────
# main
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("ENV TELEGRAM_TOKEN не задан")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    # добавь другие хэндлеры тут

    log.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

