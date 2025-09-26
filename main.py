# main.py — GPT версия с историей промтов
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

# ───────────────────────────────
# Логи
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

# ───────────────────────────────
# Переменные окружения
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ───────────────────────────────
# OpenAI GPT
from openai import OpenAI
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

def _gpt_text(prompt: str, *, temperature: float = 0.7, max_tokens: int = 200) -> Optional[str]:
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": (
                     "Ты редактор промтов для генерации коротких видеосцен. "
                     "Никогда не используй кавычки и тире. "
                     "Пиши 1–2 предложения, добавляй детали камеры/света/движения/настроения."
                 )},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        log.error("OpenAI error: %s", e)
        return None

def improve_prompt(user_text: str, mode="normal") -> str:
    sys = {
        "normal": "Сделай сцену кинематографичной.",
        "absurd": "Сделай сцену максимально абсурдной и смешной.",
        "simple": "Сделай сцену проще и реалистичнее, как будто бытовое видео.",
    }
    text = _gpt_text(f"{sys.get(mode,'normal')}\nИсходный текст: {user_text}")
    return text or user_text

# ───────────────────────────────
# Состояние пользователя
user_state: dict[int, dict] = {}

def _ensure(uid: int):
    if uid not in user_state:
        user_state[uid] = {
            "mode": None,
            "prompt": None,
            "style": None,
            "replica": None,
            "awaiting_prompt": False,
            "history": [],       # список всех промтов
            "history_index": -1  # позиция в истории
        }

# ───────────────────────────────
# Клавиатуры
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео", callback_data="menu_make")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("📚 Гайды", callback_data="menu_guides")],
    ])

def kb_after_prompt():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="prompt_absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="prompt_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="prompt_retry"),
         InlineKeyboardButton("➡️ Дальше", callback_data="choose_style")],
        [InlineKeyboardButton("⬅️ Предыдущий", callback_data="history_prev"),
         InlineKeyboardButton("➡️ Следующий", callback_data="history_next")],
    ])

def kb_styles():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Кино", callback_data="style_Cinema"),
         InlineKeyboardButton("📺 Док", callback_data="style_Doc")],
        [InlineKeyboardButton("🎨 Арт", callback_data="style_Art"),
         InlineKeyboardButton("🕶️ Ч/Б", callback_data="style_BW")],
        [InlineKeyboardButton("🌌 Киберпанк", callback_data="style_Cyberpunk"),
         InlineKeyboardButton("✨ Pixar", callback_data="style_Pixar")],
        [InlineKeyboardButton("🎤 ASMR", callback_data="style_ASMR"),
         InlineKeyboardButton("🏷️ Бренд", callback_data="style_Brand")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_after_prompt")],
    ])

# ───────────────────────────────
# Хэндлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    await update.message.reply_text("👋 Привет! Я бот для генерации видео.", reply_markup=kb_main())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    st = user_state[uid]
    text = (update.message.text or "").strip()

    if st["awaiting_prompt"]:
        st["awaiting_prompt"] = False
        new_prompt = improve_prompt(text)
        st["prompt"] = new_prompt
        st["history"].append(new_prompt)
        st["history_index"] = len(st["history"]) - 1
        await update.message.reply_text(f"📝 Промт улучшен:\n\n{new_prompt}", reply_markup=kb_after_prompt())
        return

    await update.message.reply_text("Выбери действие:", reply_markup=kb_main())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    _ensure(uid)
    st = user_state[uid]
    data = q.data
    log.info("Button: %s", data)

    if data == "menu_make":
        st.update({"mode": "helper", "prompt": None, "style": None})
        st["awaiting_prompt"] = True
        await q.message.reply_text("Опиши сцену — я помогу улучшить."); return

    if data == "mode_meme":
        st.update({"mode": "meme", "prompt": "Бабка гонится за динозавром на базаре.", "style": "Мемный"})
        st["history"].append(st["prompt"])
        st["history_index"] = len(st["history"]) - 1
        await q.message.reply_text(f"Мемный промт готов:\n\n{st['prompt']}", reply_markup=kb_after_prompt()); return

    if data == "menu_guides":
        await q.message.reply_text("Скоро тут будут гайды ❤️", reply_markup=kb_main()); return

    # Варианты промта
    if data in ["prompt_absurd", "prompt_simple", "prompt_retry"]:
        mode = "absurd" if data == "prompt_absurd" else "simple" if data == "prompt_simple" else "normal"
        new_prompt = improve_prompt(st["prompt"], mode=mode)
        st["prompt"] = new_prompt
        st["history"].append(new_prompt)
        st["history_index"] = len(st["history"]) - 1
        await q.message.reply_text(f"📝 Новый вариант:\n\n{new_prompt}", reply_markup=kb_after_prompt()); return

    # История
    if data == "history_prev":
        if st["history_index"] > 0:
            st["history_index"] -= 1
            prev_prompt = st["history"][st["history_index"]]
            st["prompt"] = prev_prompt
            await q.message.reply_text(f"⬅️ Предыдущий:\n\n{prev_prompt}", reply_markup=kb_after_prompt())
        else:
            await q.message.reply_text("❌ Это первый промт.", reply_markup=kb_after_prompt())
        return

    if data == "history_next":
        if st["history_index"] < len(st["history"]) - 1:
            st["history_index"] += 1
            next_prompt = st["history"][st["history_index"]]
            st["prompt"] = next_prompt
            await q.message.reply_text(f"➡️ Следующий:\n\n{next_prompt}", reply_markup=kb_after_prompt())
        else:
            await q.message.reply_text("❌ Дальше нет.", reply_markup=kb_after_prompt())
        return

    # Стили
    if data == "choose_style":
        await q.message.reply_text("Выберите стиль:", reply_markup=kb_styles()); return
    if data.startswith("style_"):
        st["style"] = data.split("style_", 1)[1]
        await q.message.reply_text(f"🎨 Стиль выбран: {st['style']}", reply_markup=kb_after_prompt()); return
    if data == "back_after_prompt":
        await q.message.reply_text("Дальше что делаем?", reply_markup=kb_after_prompt()); return

# ───────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN не задан")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    log.info("Bot is running…")
    app.run_polling()

if __name__ == "__main__":
    main()

