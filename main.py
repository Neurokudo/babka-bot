# main.py — версия без Gemini, с GPT (OpenAI)
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
# .env (локально); на Railway берутся Variables
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# Логи
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

# ──────────────────────────────────────────────────────────────
# Пользовательский стейт
user_state: dict[int, dict] = {}
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "Кино")

def _ensure_state(uid: int):
    if uid not in user_state:
        user_state[uid] = {
            "mode": None,                   # helper | manual | meme
            "prompt": None,                 # текущий промт
            "style": None,                  # стиль
            "replica": None,                # реплика
            "awaiting_prompt": False,       # ждём текст сцены
            "awaiting_replica": False,      # ждём ручную реплику
            "awaiting_custom_style": False, # ждём ручной стиль
        }

# ──────────────────────────────────────────────────────────────
# OpenAI (GPT)
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client: Optional[OpenAI] = None

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI enabled (GPT provider).")
    except Exception as e:
        log.error("OpenAI init failed: %s", e)
        openai_client = None
else:
    log.warning("OPENAI_API_KEY is not set. GPT features disabled.")

def _gpt_text(prompt: str, *, temperature: float = 0.7, max_tokens: int = 256) -> Optional[str]:
    """Единый вызов GPT для короткого текста."""
    if not openai_client:
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # быстрый и недорогой; можно заменить на gpt-4o
            messages=[
                {"role": "system",
                 "content": "Ты редактор промтов для генерации коротких видеосцен. Пиши ясно и без лишней воды."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out or None
    except Exception as e:
        log.error("OpenAI error: %s", e)
        return None

def improve_prompt(user_text: str) -> tuple[str, bool]:
    """Вернуть улучшенный промт и флаг успеха."""
    sys = (
        "Перепиши текст сцены для генерации КОРОТКОГО видео (1–2 предложения). "
        "Добавь детали камеры/света/движения/настроения. "
        "Запрещено: любой экранный текст/водяные знаки."
    )
    out = _gpt_text(f"{sys}\nИсходный текст: {user_text}", temperature=0.65, max_tokens=140)
    return (out, True) if out else (user_text, False)

def suggest_replica(prompt_text: str) -> Optional[str]:
    """Одна короткая реплика героя (4–10 слов), без кавычек и комментариев."""
    sys = "Придумай ОДНУ короткую реплику персонажа (4–10 слов) к сцене. Только фраза, без кавычек."
    return _gpt_text(f"{sys}\nСцена: {prompt_text}", temperature=0.9, max_tokens=40)

# ──────────────────────────────────────────────────────────────
# Veo клиент (оставляем как есть)
from veo_client import generate_video_sync

# ──────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────
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
    text = (update.message.text or "").strip()

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
        if st["mode"] == "helper" and openai_client:
            improved, ok = improve_prompt(text)
            st["prompt"] = improved
            if ok:
                await update.message.reply_text(
                    f"📝 Промт улучшен:\n\n{improved}",
                    reply_markup=kb_after_prompt()
                )
            else:
                await update.message.reply_text(
                    "⚠️ GPT сейчас недоступен. Сохраняю промт без изменений:\n\n" + improved,
                    reply_markup=kb_after_prompt()
                )
        else:
            st["prompt"] = text
            await update.message.reply_text(
                f"📝 Промт сохранён:\n\n{text}",
                reply_markup=kb_after_prompt()
            )
        return

    # если ничего не ждём — меню
    await update.message.reply_text("Выбери действие:", reply_markup=kb_main())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    _ensure_state(uid)
    st = user_state[uid]
    data = query.data
    log.info("Button: %s", data)

    # Главное меню
    if data == "menu_make":
        await query.edit_message_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await query.edit_message_text("Фича «Оживление изображения» пока выключена.", reply_markup=kb_main()); return
    if data == "menu_guides":
        await query.edit_message_text("Скоро тут будут гайды и оплата ❤️", reply_markup=kb_main()); return
    if data == "menu_profile":
        await query.edit_message_text("Профиль / Баланс — в разработке.", reply_markup=kb_main()); return
    if data == "back_main":
        await query.edit_message_text("Главное меню:", reply_markup=kb_main()); return

    # Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "prompt": None, "style": None, "replica": None})
        st["awaiting_prompt"] = True
        await query.edit_message_text("Опиши сцену — я помогу дописать детали. Жду промт 👇"); return
    if data == "mode_manual":
        st.update({"mode": "manual", "prompt": None, "style": None, "replica": None})
        st["awaiting_prompt"] = True
        await query.edit_message_text("Введи промт для видео 👇"); return
    if data == "mode_meme":
        st.update({"mode": "meme", "prompt": "Смешная динамичная сцена, быстрая смена планов.",
                   "style": "Мемный стиль", "replica": "Ну держитесь теперь!"})
        await query.edit_message_text("Мемный режим готов. Можно генерировать.", reply_markup=kb_after_prompt()); return
    if data == "back_modes":
        await query.edit_message_text("Выберите режим генерации:", reply_markup=kb_modes()); return

    # После промта
    if data == "choose_style":
        await query.edit_message_text("Выберите стиль:", reply_markup=kb_style_list()); return
    if data == "back_after_prompt":
        await query.edit_message_text("Дальше что делаем?", reply_markup=kb_after_prompt()); return

    if data.startswith("style_"):
        st["style"] = data.split("style_", 1)[1]
        await query.edit_message_text(f"🎨 Стиль выбран: {st['style']}", reply_markup=kb_after_prompt()); return
    if data == "style_custom":
        st["awaiting_custom_style"] = True
        await query.edit_message_text("Введи стиль текстом 👇"); return

    # Реплика
    if data == "replica_menu":
        await query.edit_message_text("Выбери способ добавить реплику:", reply_markup=kb_replica_menu()); return
    if data == "replica_custom":
        st["awaiting_replica"] = True
        await query.edit_message_text("Введи текст реплики 👇"); return
    if data == "replica_ai":
        if not st.get("prompt"):
            await query.edit_message_text("Сначала введи промт, потом предложу реплику.", reply_markup=kb_after_prompt()); return
        text = suggest_replica(st["prompt"]) or "Ну держитесь теперь!"
        st["replica"] = text
        await query.edit_message_text(f"💬 Реплика предложена: {text}", reply_markup=kb_after_prompt()); return

    # Генерация
    if data == "generate_now":
        if not st.get("prompt"):
            await query.edit_message_text("Сначала введи промт.", reply_markup=kb_after_prompt()); return
        if not st.get("style"):
            st["style"] = DEFAULT_STYLE
        await query.edit_message_text("⏳ Генерирую видео в Veo 3… это может занять немного времени.")
        try:
            mp4_path = await context.application.run_in_executor(
                None, generate_video_sync, st["prompt"], st["style"], st.get("replica"), 8
            )
            caption = (
                "✅ Готово!\n\n"
                f"📝 Промт: {st['prompt']}\n"
                f"🎨 Стиль: {st['style']}" + (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "")
            )
            with open(mp4_path, "rb") as f:
                await query.message.reply_video(video=f, caption=caption, supports_streaming=True)
        except Exception as e:
            log.exception("Veo generation failed")
            await query.message.reply_text(f"❌ Ошибка генерации: {e}")
        finally:
            await query.message.reply_text("Что дальше?", reply_markup=kb_after_prompt())
        return

    # Фолбэк
    await query.edit_message_text(f"Неизвестная кнопка: {data}", reply_markup=kb_main())

# ──────────────────────────────────────────────────────────────
# Отладка всех апдейтов
async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("DEBUG UPDATE: %s", update)

# ──────────────────────────────────────────────────────────────
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("ENV TELEGRAM_TOKEN не задан")

    app = Application.builder().token(token).build()

    # Отладка в самом раннем group
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=-1)

    # Команды/кнопки/тексты
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    log.info("Bot is running…")
    app.run_polling()

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

