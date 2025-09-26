# main.py — Стартовое меню, режимы, GPT-сцены на ~8 сек, мемный режим, стили/реплики, реальная генерация (Veo)
import os
import random
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

# ========= БАЗА / ОКРУЖЕНИЕ =========
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_STYLE = "Кино"

# ========= OPENAI (GPT) =========
from openai import OpenAI
gpt: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        gpt = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI GPT активирован.")
    except Exception as e:
        log.error("OpenAI init error: %s", e)

def _sanitize(text: str) -> str:
    if not text:
        return text
    # убрать кавычки и тире всех видов
    bad = ['"', '«', '»', '„', '“', '‟', '‹', '›', "'", '’', '‚', '‛', '‐', '-', '‒', '–', '—', '―']
    for ch in bad:
        text = text.replace(ch, "")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _gpt(system: str, user: str, temperature=0.7, max_tokens=220) -> Optional[str]:
    if not gpt:
        return None
    try:
        r = gpt.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = (r.choices[0].message.content or "").strip()
        return _sanitize(out)
    except Exception as e:
        log.error("GPT error: %s", e)
        return None

# — Сцена на ~8 секунд, максимум 2 смены плана, без эмо-поэзии
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "absurd": "Сделай сцену более абсурдной и смешной.",
        "simple": "Сделай сцену проще и короче.",
    }.get(mode, "Сделай рабочую сцену.")
    sys = (
        "Ты редактор коротких видео-сцен. "
        "Формулируй именно СЦЕНУ (что, где, кто, какое действие). "
        "Длительность ~8 секунд, максимум две смены плана. "
        "Без поэтических эмоций, только действие и визуальные детали. "
        "Запрещены текст/субтитры/водяные знаки в кадре. "
        "СТРОГО не используй кавычки и тире. "
        f"{style} Напиши 1–2 кратких предложения."
    )
    out = _gpt(sys, user_text, temperature=0.65 if mode != "absurd" else 0.9, max_tokens=140)
    return out or _sanitize(user_text)

def suggest_replica(scene: str) -> Optional[str]:
    sys = "Придумай короткую реплику героя (4–10 слов) к сцене. Только сама фраза. Без кавычек и тире."
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ========= VEO (реальная генерация) =========
from veo_client import generate_video_sync  # ожидается: def generate_video_sync(prompt, style, replica, duration)->str

# ========= СОСТОЯНИЕ =========
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        users[uid] = {
            "mode": None,
            "source_text": None,   # исходный ввод пользователя
            "scene": None,         # текущая сцена
            "style": None,
            "replica": None,
            "awaiting_scene": False,
            "awaiting_custom_style": False,
        }

# ========= КЛАВИАТУРЫ =========
def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео с помощником", callback_data="menu_make")],
        [InlineKeyboardButton("🖼️ Оживление изображения", callback_data="menu_alive")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
        [InlineKeyboardButton("👤 Профиль / Баланс", callback_data="menu_profile")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="mode_helper")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="var_absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="var_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("🎨 Выбрать стиль", callback_data="choose_style")],
    ])

def kb_styles():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Кино", callback_data="style_Кино"),
         InlineKeyboardButton("📺 Документальный", callback_data="style_Документальный")],
        [InlineKeyboardButton("🎤 ASMR", callback_data="style_ASMR"),
         InlineKeyboardButton("🏷️ Бренд", callback_data="style_Бренд")],
        [InlineKeyboardButton("🎨 Арт / Ретро / ЧБ", callback_data="style_Арт/Ретро/ЧБ"),
         InlineKeyboardButton("🤖 Киберпанк", callback_data="style_Киберпанк")],
        [InlineKeyboardButton("✨ Pixar", callback_data="style_Pixar"),
         InlineKeyboardButton("✏️ Другой стиль", callback_data="style_custom")],
        [InlineKeyboardButton("🚀 Без стиля — генерировать", callback_data="style_None")],
    ])

def kb_after_style():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="add_replica")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")],
    ])

def kb_meme():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить ещё", callback_data="meme_again")],
        [InlineKeyboardButton("🧠✨ Улучшить с помощником", callback_data="meme_to_helper")],
        [InlineKeyboardButton("🎨 Выбрать стиль", callback_data="choose_style")],
    ])

# ========= МЕМНЫЙ РЕЖИМ =========
def random_meme_scene() -> str:
    subjects = ["Бабка", "Старушка", "Бабуля"]
    mounts = ["на осле", "на страусе", "на тележке из супермаркета", "на скейтборде"]
    spots  = ["на рынке", "в метро", "на стадионе", "в аквапарке", "у подъезда"]
    actions = ["спорит с охраной", "гонится за голубем", "торгуется до копейки", "чешет страуса ложкой"]
    s = f"{random.choice(subjects)} {random.choice(mounts)} {random.choice(spots)} {random.choice(actions)}"
    return _sanitize(s)

# ========= ХЭНДЛЕРЫ =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    users[uid].update({"mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
                       "awaiting_scene": False, "awaiting_custom_style": False})
    # два сообщения как на твоём скрине
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_home())
    await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
        await update.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())
        return

    if st["awaiting_scene"]:
        st["awaiting_scene"] = False
        st["source_text"] = text
        if st["mode"] == "helper" and gpt:
            scene = improve_scene(text, mode="normal")
        else:
            scene = text
        st["scene"] = scene
        await update.message.reply_text(f"📝 Промт улучшен:\n\n{scene}", reply_markup=kb_variants())
        return

    # если текст пришёл вне контекста — показать меню
    await update.message.reply_text("Главное меню:", reply_markup=kb_home())
    await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    _ensure(uid)
    st = users[uid]
    data = q.data
    log.info("Button: %s", data)

    # --- Главное меню
    if data == "menu_make":
        await q.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await q.message.reply_text("🖼️ Оживление изображения: пришлите фото и короткий промт (функция в разработке)."); return
    if data == "menu_guides":
        await q.message.reply_text("📚 Гайды и оплата — скоро тут ❤️"); return
    if data == "menu_profile":
        await q.message.reply_text("👤 Профиль/Баланс — скоро доступно."); return
    if data == "back_home":
        await q.message.reply_text("Главное меню:", reply_markup=kb_home()); return

    # --- Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.reply_text("🧠✨ Опиши сцену — я сделаю её съёмочной на ~8 секунд.")
        return
    if data == "mode_manual":
        st.update({"mode": "manual", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.reply_text("✍️ Введи свою сцену (я ничего не буду менять).")
        return
    if data == "mode_meme":
        st.update({"mode": "meme", "style": None, "replica": None})
        scene = random_meme_scene()
        st["scene"] = scene
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{scene}", reply_markup=kb_meme())
        return

    # --- Варианты сцены (GPT)
    if data in ("var_absurd", "var_simple", "var_again"):
        scene = st.get("scene")
        if not scene:
            await q.message.reply_text("Сначала опиши сцену."); return
        if data == "var_absurd":
            st["scene"] = improve_scene(scene, mode="absurd")
            title = "Вариант (абсурднее)"
        elif data == "var_simple":
            st["scene"] = improve_scene(scene, mode="simple")
            title = "Вариант (проще)"
        else:  # var_again
            base = st.get("source_text") or scene
            st["scene"] = improve_scene(base, mode="normal")
            title = "Новый вариант"
        await q.message.reply_text(f"✏️ {title}:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Мемный режим кнопки
    if data == "meme_again":
        st["scene"] = random_meme_scene()
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{st['scene']}", reply_markup=kb_meme())
        return
    if data == "meme_to_helper":
        st["scene"] = improve_scene(st.get("scene", ""), mode="normal")
        st["mode"] = "helper"
        await q.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Стили
    if data == "choose_style":
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles()); return
    if data.startswith("style_"):
        val = data.split("_", 1)[1]
        st["style"] = None if val == "None" else val
        await q.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
        await q.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())
        return
    if data == "style_custom":
        st["awaiting_custom_style"] = True
        await q.message.reply_text("Введи свой стиль текстом:"); return

    # --- Реплика
    if data == "add_replica":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        text = suggest_replica(st["scene"]) or "Поехали уже!"
        st["replica"] = text
        await q.message.reply_text(f"💬 Реплика предложена: {text}")
        # оставим компактную клавиатуру для шага генерации
        await q.message.reply_text("Готово! Можно генерировать.", reply_markup=kb_after_style())
        return

    # --- Генерация видео (реально Veo)
    if data == "generate_now":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None:
            st["style"] = DEFAULT_STYLE

        await q.message.reply_text("⏳ Генерирую видео…")
        try:
            # Генерим 8 секунд, как в правилах сцен
            mp4_path = await asyncio.to_thread(
                generate_video_sync, st["scene"], st["style"], st.get("replica"), 8
            )
            caption = f"✅ Готово!\n\n📝 Сцена: {st['scene']}\n🎨 Стиль: {st['style']}" + \
                      (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "")
            with open(mp4_path, "rb") as f:
                await q.message.reply_video(video=f, caption=caption, supports_streaming=True)
        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"❌ Ошибка генерации: {e}")
        return

    # fallback
    await q.message.reply_text("Команда пока не поддерживается. Возврат в меню.", reply_markup=kb_home())
    await q.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes())

# ========= ЗАПУСК =========
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Bot is running…")
    app.run_polling()

if __name__ == "__main__":
    main()

