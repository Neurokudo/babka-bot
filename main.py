# main.py — GPT версия, продуманная логика кнопок, история промтов, расширенные стили
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

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

# ─────────────────────────────────────────────────────────────
# БАЗА
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "Кино")

# ─────────────────────────────────────────────────────────────
# OPENAI (GPT)
from openai import OpenAI
openai_client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI enabled (GPT provider).")
    except Exception as e:
        log.error("OpenAI init failed: %s", e)

def _sanitize_no_quotes_dashes(text: str) -> str:
    """Убираем любые кавычки и тире/деши — для корректной озвучки."""
    if not text:
        return text
    bad = ['"', '«', '»', '„', '“', '‟', '‹', '›', "'", '’', '‚', '‛', '‐', '-', '‒', '–', '—', '―']
    for ch in bad:
        text = text.replace(ch, "")
    # уберем двойные пробелы, точки по 2+
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _gpt_text(prompt: str, *, temperature: float = 0.7, max_tokens: int = 256) -> Optional[str]:
    """Единый вызов GPT (короткие ответы)."""
    if not openai_client:
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": (
                     "Ты редактор промтов для генерации коротких видеосцен. "
                     "Пиши 1–2 предложения, добавляй детали камеры, света, движения и настроения. "
                     "СТРОГО: не используй кавычки и не используй тире. "
                     "Запрещены экранные надписи и водяные знаки."
                 )},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = (resp.choices[0].message.content or "").strip()
        return _sanitize_no_quotes_dashes(out) if out else None
    except Exception as e:
        log.error("OpenAI error: %s", e)
        return None

def improve_prompt(user_text: str, mode: str = "normal") -> str:
    """Переписывает сцену: normal | absurd | simple."""
    flavor = {
        "normal": "Сделай сцену кинематографичной и цельной.",
        "absurd": "Сделай сцену абсурдной и смешной, усили элемент неожиданности.",
        "simple": "Сделай сцену проще и реалистичнее, будто бытовое видео.",
    }.get(mode, "Сделай сцену кинематографичной и цельной.")
    sys = f"{flavor} Сохрани короткий формат в 1–2 предложения. Запрещён любой текст в кадре."
    out = _gpt_text(f"{sys}\nИсходный текст: {user_text}",
                    temperature=0.9 if mode == "absurd" else 0.65,
                    max_tokens=140)
    return out or user_text

def suggest_replica(prompt_text: str) -> Optional[str]:
    """Одна короткая реплика героя (4–10 слов), без кавычек и тире."""
    sys = "Придумай ОДНУ короткую реплику героя (4–10 слов) к сцене. Только сама фраза."
    out = _gpt_text(f"{sys}\nСцена: {prompt_text}", temperature=0.9, max_tokens=40)
    return _sanitize_no_quotes_dashes(out) if out else None

# ─────────────────────────────────────────────────────────────
# VEO (локальный клиент — синхронный)
from veo_client import generate_video_sync

# ─────────────────────────────────────────────────────────────
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        users[uid] = {
            "mode": None,                   # helper | manual | meme
            "prompt": None,
            "style": None,
            "replica": None,
            "awaiting_prompt": False,
            "awaiting_replica": False,
            "awaiting_custom_style": False,
            "history": [],                 # история вариантов сцены
            "history_index": -1,
        }

# ─────────────────────────────────────────────────────────────
# КЛАВИАТУРЫ
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создать видео", callback_data="menu_make")],
        [InlineKeyboardButton("🧠 Умный помощник", callback_data="mode_helper"),
         InlineKeyboardButton("✍️ Я сам", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Умный помощник", callback_data="mode_helper"),
         InlineKeyboardButton("✍️ Я сам", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_main")],
    ])

def kb_after_prompt():
    # Эти кнопки важны пользователю — оставляем сообщение в чате.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="prompt_absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="prompt_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="prompt_retry"),
         InlineKeyboardButton("➡️ Дальше", callback_data="choose_style")],
        [InlineKeyboardButton("⬅️ Предыдущий", callback_data="history_prev"),
         InlineKeyboardButton("➡️ Следующий", callback_data="history_next")],
    ])

def kb_style_list():
    # Расширенный список стилей (как просил)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Кино", callback_data="style_Кино"),
         InlineKeyboardButton("📺 Документальный", callback_data="style_Документальный")],
        [InlineKeyboardButton("🎤 ASMR", callback_data="style_ASMR"),
         InlineKeyboardButton("🏷️ Бренд", callback_data="style_Бренд")],
        [InlineKeyboardButton("🎨 Арт / Ретро / ЧБ", callback_data="style_Арт/Ретро/ЧБ"),
         InlineKeyboardButton("🤖 Киберпанк", callback_data="style_Киберпанк")],
        [InlineKeyboardButton("✨ Pixar", callback_data="style_Pixar"),
         InlineKeyboardButton("✏️ Другой стиль (ввести)", callback_data="style_custom")],
        [InlineKeyboardButton("🚀 Без стиля — генерировать", callback_data="generate_now")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_after_prompt")],
    ])

def kb_replica_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Введу сам", callback_data="replica_custom"),
         InlineKeyboardButton("🤖 Пусть бот предложит", callback_data="replica_ai")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_after_prompt")],
    ])

# ─────────────────────────────────────────────────────────────
# ХЭНДЛЕРЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    users[uid].update({
        "mode": None, "prompt": None, "style": None, "replica": None,
        "awaiting_prompt": False, "awaiting_replica": False, "awaiting_custom_style": False,
        "history": [], "history_index": -1,
    })
    # Старт — это важная точка, оставляем клавиатуру
    await update.message.reply_text("👋 Привет! Я помогу быстро собрать промт и сгенерировать видео.", reply_markup=kb_main())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = (update.message.text or "").strip()

    # 1) Кастомный стиль
    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"🎨 Стиль сохранён: {text}", reply_markup=kb_after_prompt())
        return

    # 2) Ручная реплика
    if st["awaiting_replica"]:
        st["awaiting_replica"] = False
        st["replica"] = _sanitize_no_quotes_dashes(text)
        await update.message.reply_text(f"💬 Реплика сохранена: {st['replica']}", reply_markup=kb_after_prompt())
        return

    # 3) Промт
    if st["awaiting_prompt"]:
        st["awaiting_prompt"] = False
        if st["mode"] == "helper" and openai_client:
            new_prompt = improve_prompt(text, mode="normal")
            st["prompt"] = new_prompt
            st["history"].append(new_prompt)
            st["history_index"] = len(st["history"]) - 1
            await update.message.reply_text(f"📝 Промт улучшен:\n\n{new_prompt}", reply_markup=kb_after_prompt())
        else:
            st["prompt"] = text
            st["history"].append(text)
            st["history_index"] = len(st["history"]) - 1
            await update.message.reply_text(f"📝 Промт сохранён:\n\n{text}", reply_markup=kb_after_prompt())
        return

    # 4) Фолбэк — возвращаемся к меню (оставляем клавиатуру)
    await update.message.reply_text("Выбери действие:", reply_markup=kb_main())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    data = q.data
    log.info("Button: %s", data)

    # ── МЕНЮ / РЕЖИМЫ ───────────────────────────────────────
    if data == "menu_make":
        await q.message.reply_text("Выберите режим:", reply_markup=kb_modes()); return

    if data == "back_main":
        await q.message.reply_text("Главное меню:", reply_markup=kb_main()); return

    if data == "mode_helper":
        st.update({"mode": "helper", "prompt": None, "style": None, "replica": None,
                   "history": [], "history_index": -1})
        st["awaiting_prompt"] = True
        # Техническая подсказка — без клавиатуры
        await q.message.reply_text("Опиши сцену — я помогу улучшить.")
        return

    if data == "mode_manual":
        st.update({"mode": "manual", "prompt": None, "style": None, "replica": None,
                   "history": [], "history_index": -1})
        st["awaiting_prompt"] = True
        await q.message.reply_text("Введи промт для видео.")
        return

    if data == "mode_meme":
        st.update({"mode": "meme", "style": "Мемный"})
        st["prompt"] = "Бабка гонится за динозавром по базару, камера дергается, шум толпы и паника."
        st["history"] = [st["prompt"]]
        st["history_index"] = 0
        await q.message.reply_text(f"Мемный промт готов:\n\n{st['prompt']}", reply_markup=kb_after_prompt())
        return

    if data == "menu_guides":
        await q.message.reply_text("Скоро тут будут гайды и оплата ❤️", reply_markup=kb_main()); return

    # ── ВАРИАНТЫ ПРОМТА ─────────────────────────────────────
    if data in ("prompt_absurd", "prompt_simple", "prompt_retry"):
        if not st.get("prompt"):
            await q.message.reply_text("Сначала введи промт.", reply_markup=kb_main()); return
        mode = "absurd" if data == "prompt_absurd" else "simple" if data == "prompt_simple" else "normal"
        new_prompt = improve_prompt(st["prompt"], mode=mode)
        st["prompt"] = new_prompt
        st["history"].append(new_prompt)
        st["history_index"] = len(st["history"]) - 1
        title = "Вариант (абсурднее)" if mode == "absurd" else "Вариант (проще)" if mode == "simple" else "Новый вариант"
        await q.message.reply_text(f"📝 {title}:\n\n{new_prompt}", reply_markup=kb_after_prompt())
        return

    # ── ИСТОРИЯ ─────────────────────────────────────────────
    if data == "history_prev":
        if st["history_index"] > 0:
            st["history_index"] -= 1
            st["prompt"] = st["history"][st["history_index"]]
            await q.message.reply_text(f"⬅️ Предыдущий:\n\n{st['prompt']}", reply_markup=kb_after_prompt())
        else:
            await q.message.reply_text("❌ Это первый промт.", reply_markup=kb_after_prompt())
        return

    if data == "history_next":
        if st["history_index"] < len(st["history"]) - 1:
            st["history_index"] += 1
            st["prompt"] = st["history"][st["history_index"]]
            await q.message.reply_text(f"➡️ Следующий:\n\n{st['prompt']}", reply_markup=kb_after_prompt())
        else:
            await q.message.reply_text("❌ Дальше нет.", reply_markup=kb_after_prompt())
        return

    # ── СТИЛИ ───────────────────────────────────────────────
    if data == "choose_style":
        await q.message.reply_text("Выберите стиль:", reply_markup=kb_style_list()); return

    if data == "back_after_prompt":
        await q.message.reply_text("Дальше что делаем?", reply_markup=kb_after_prompt()); return

    if data == "style_custom":
        st["awaiting_custom_style"] = True
        await q.message.reply_text("Введи свой стиль текстом."); return

    if data.startswith("style_"):
        st["style"] = data.split("style_", 1)[1]
        await q.message.reply_text(f"🎨 Стиль выбран: {st['style']}", reply_markup=kb_after_prompt()); return

    # ── РЕПЛИКА ─────────────────────────────────────────────
    if data == "replica_menu":
        await q.message.reply_text("Добавим реплику?", reply_markup=kb_replica_menu()); return

    if data == "replica_custom":
        st["awaiting_replica"] = True
        await q.message.reply_text("Введи текст реплики (коротко, 4–10 слов)."); return

    if data == "replica_ai":
        if not st.get("prompt"):
            await q.message.reply_text("Сначала введи промт.", reply_markup=kb_after_prompt()); return
        text = suggest_replica(st["prompt"]) or "Ну держитесь теперь!"
        st["replica"] = text
        await q.message.reply_text(f"💬 Реплика предложена: {text}", reply_markup=kb_after_prompt()); return

    # ── ГЕНЕРАЦИЯ ───────────────────────────────────────────
    if data == "generate_now":
        if not st.get("prompt"):
            await q.message.reply_text("Сначала введи промт.", reply_markup=kb_after_prompt()); return
        if not st.get("style"):
            st["style"] = DEFAULT_STYLE

        # Техническое сообщение — оно одноразовое, без клавиатуры
        wait_msg = await q.message.reply_text("⏳ Генерирую видео в Veo 3…")

        try:
            mp4_path = await asyncio.to_thread(
                generate_video_sync, st["prompt"], st["style"], st.get("replica"), 8
            )
            caption = (
                "✅ Готово!\n\n"
                f"📝 Промт: {st['prompt']}\n"
                f"🎨 Стиль: {st['style']}" + (f"\n💬 Реплика: {st['replica']']}" if st.get("replica") else "")
            )
            # отправляем видео отдельным сообщением
            with open(mp4_path, "rb") as f:
                await q.message.reply_video(video=f, caption=caption, supports_streaming=True)
        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"❌ Ошибка генерации: {e}")
        finally:
            # завершающее сообщение с «что дальше» — оставляем клавиатуру
            await q.message.reply_text("Что дальше?", reply_markup=kb_after_prompt())
        return

    # ── ФОЛБЭК ──────────────────────────────────────────────
    await q.message.reply_text(f"Неизвестная кнопка: {data}", reply_markup=kb_main())

# ─────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("ENV TELEGRAM_TOKEN не задан")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    log.info("Bot is running…")
    app.run_polling()

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

