# main.py
import os
import logging
import random
from pathlib import Path

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

# ── Загрузка .env (строго из папки, где лежит этот файл)
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# ── Логирование
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("babka-bot")

# ── Gemini (LLM)
import google.generativeai as genai

# ── Veo client (лежит рядом: veo_client.py)
from veo_client import generate_video_sync

# ──────────────────────────────────────────────────────────────────────────────
# Глобальное состояние пользователя
# user_state[user_id] = {"mode":..., "prompt":..., "style":..., "replica":..., flags...}
user_state = {}
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "cinema")

def _ensure_state(user_id: int):
    if user_id not in user_state:
        user_state[user_id] = {
            "mode": None,
            "prompt": None,
            "style": None,
            "replica": None,
            "awaiting_replica": False,
            "awaiting_custom_style": False,
        }

# ──────────────────────────────────────────────────────────────────────────────
# Gemini init (по ключу)
GEMINI_ENABLED = os.getenv("LLM_PROVIDER") == "gemini" and bool(os.getenv("GOOGLE_API_KEY"))
if GEMINI_ENABLED:
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        log.info("Gemini enabled.")
    except Exception as e:
        gemini_model = None
        log.warning(f"Gemini init failed: {e}")
else:
    gemini_model = None

def suggest_replica(prompt: str) -> str:
    if not gemini_model:
        return "Ну держитесь теперь!"
    try:
        resp = gemini_model.generate_content(
            f"Придумай короткую (до 15 слов) смешную, живую реплику персонажа к этому описанию сцены. "
            f"Без кавычек и эмодзи. Описание: {prompt}"
        )
        text = (resp.text or "").strip()
        return text or "Ну держитесь теперь!"
    except Exception as e:
        log.warning(f"Gemini error: {e}")
        return "Ну держитесь теперь!"

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
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_main")],
    ])

def kb_after_prompt():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Выбрать стиль", callback_data="prompt_to_styles")],
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="choose_replica")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="back_modes")],
    ])

def kb_replica_options():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Введу сам текст", callback_data="replica_manual")],
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
        [InlineKeyboardButton("➕ Другой стиль (ввести)", callback_data="style_more")],
        [InlineKeyboardButton("🚀 Без стиля — генерировать", callback_data="style_skip_generate")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="back_modes")],
    ])

def kb_after_video():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить промт", callback_data="edit_prompt")],
        [InlineKeyboardButton("🎬 Создать новое видео", callback_data="new_video")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="back_main")],
    ])

# ──────────────────────────────────────────────────────────────────────────────
# Утилиты
def generate_meme_prompt():
    subjects = [
        "Бабка","Дед","Гламурная девица","Неформал","Рокер","Строитель",
        "Слон","Носорог","Бегемот","Капибара","Динозавр","Суровая бизнес-вумен",
        "Официант","Футболист","Школьник с рюкзаком","Мужик в телогрейке",
        "Тётка с авоськой","Дворник","Рэпер в кепке","Повар в колпаке",
        "Охранник в форме","Курьер на велике"
    ]
    actions = ["едет верхом","падает","кричит","танцует","спорит","машет руками"]
    objects = ["на свинье","с огромным самоваром","рядом с холодильником","с портретом Ленина"]
    locations = ["в деревне","в панельном районе","на стадионе","у бассейна","на стройке"]
    return f"{random.choice(subjects)} {random.choice(actions)} {random.choice(objects)} {random.choice(locations)}"

# ──────────────────────────────────────────────────────────────────────────────
# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _ensure_state(user_id)
    await update.message.reply_text("👋 Привет! Я бот для генерации видео.", reply_markup=kb_main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши описание сцены текстом → выбери стиль → нажми «Сгенерировать сейчас».")

# ──────────────────────────────────────────────────────────────────────────────
# Генерация видео через Veo
async def generate_video(query, context):
    user_id = query.from_user.id
    _ensure_state(user_id)
    st = user_state[user_id]

    prompt = st.get("prompt") or "(пусто)"
    style  = st.get("style") or DEFAULT_STYLE
    replica = st.get("replica")

    await query.message.reply_text("⏳ Генерирую видео в Veo 3… это может занять немного времени.")

    try:
        # Вынести синхронную генерацию из event loop
        mp4_path = await context.application.run_in_executor(
            None, generate_video_sync, prompt, style, replica, 8
        )
        caption = (
            "✅ Готово!\n\n"
            f"📝 Промт: {prompt}\n"
            f"🎨 Стиль: {style}" + (f"\n💬 Реплика: {replica}" if replica else "")
        )
        with open(mp4_path, "rb") as f:
            await query.message.reply_video(
                video=f, caption=caption, supports_streaming=True, reply_markup=kb_after_video()
            )
    except Exception as e:
        log.exception("Veo generation failed")
        await query.message.reply_text(f"❌ Ошибка генерации: {e}", reply_markup=kb_after_video())

# ──────────────────────────────────────────────────────────────────────────────
# Текстовые сообщения
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _ensure_state(user_id)
    st = user_state[user_id]
    text = (update.message.text or "").strip()

    # ввод реплики?
    if st.get("awaiting_replica"):
        st["replica"] = text
        st["awaiting_replica"] = False
        await update.message.reply_text(f"✅ Реплика сохранена:\n{text}", reply_markup=kb_after_prompt())
        return

    # ввод кастомного стиля?
    if st.get("awaiting_custom_style"):
        st["style"] = text
        st["awaiting_custom_style"] = False
        await update.message.reply_text(f"🎨 Стиль установлен: {text}", reply_markup=kb_after_prompt())
        return

    # иначе — это промт
    st["prompt"] = text
    await update.message.reply_text(f"📝 Промт сохранён:\n\n{text}", reply_markup=kb_after_prompt())

# ──────────────────────────────────────────────────────────────────────────────
# Кнопки
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    _ensure_state(user_id)
    st = user_state[user_id]

    if data == "back_main":
        await query.message.reply_text("🏠 Главное меню", reply_markup=kb_main_menu()); return
    if data == "menu_create":
        await query.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "back_modes":
        await query.message.reply_text("Выберите режим:", reply_markup=kb_modes()); return

    if data == "helper":
        st["mode"] = "helper"
        await query.message.reply_text("Опиши сцену текстом — я помогу дописать детали. Жду промт 👇"); return
    if data == "manual":
        st["mode"] = "manual"
        await query.message.reply_text("Введи свой промт целиком. Жду 👇"); return
    if data == "meme_mode":
        st["mode"] = "meme"
        meme_prompt = generate_meme_prompt()
        st["prompt"] = meme_prompt
        await query.message.reply_text(f"🎲 Мемный промт:\n{meme_prompt}", reply_markup=kb_after_prompt()); return

    if data == "choose_replica":
        await query.message.reply_text("Выбери способ добавить реплику:", reply_markup=kb_replica_options()); return
    if data == "replica_manual":
        st["awaiting_replica"] = True
        await query.message.reply_text("Введи текст реплики (1–2 предложения):"); return
    if data == "replica_ai":
        if not st.get("prompt"):
            await query.message.reply_text("Сначала введи промт, потом предложу реплику.", reply_markup=kb_after_prompt()); return
        st["replica"] = suggest_replica(st["prompt"])
        await query.message.reply_text(f"💬 Реплика предложена:\n{st['replica']}", reply_markup=kb_after_prompt()); return
    if data == "replica_back":
        await query.message.reply_text("Ок. Что дальше?", reply_markup=kb_after_prompt()); return

    if data == "prompt_to_styles":
        await query.message.reply_text("Выберите стиль:", reply_markup=kb_styles()); return
    if data.startswith("style_"):
        key = data.replace("style_", "")
        if key == "more":
            st["awaiting_custom_style"] = True
            await query.message.reply_text("Введи название/описание стиля одной строкой (например: «киберпанк, неон, экшн»):")
            return
        if key == "skip_generate":
            await generate_video(query, context); return
        st["style"] = key
        await query.message.reply_text(f"🎨 Стиль выбран: {key}", reply_markup=kb_after_prompt()); return

    if data == "generate_now":
        if not st.get("prompt"):
            await query.message.reply_text("Сначала введи промт текстом.", reply_markup=kb_modes()); return
        await generate_video(query, context); return

    if data == "edit_prompt":
        await query.message.reply_text("Ок, введи новый промт:"); return
    if data == "new_video":
        user_state[user_id] = {
            "mode": None, "prompt": None, "style": None,
            "replica": None, "awaiting_replica": False,
            "awaiting_custom_style": False,
        }
        await query.message.reply_text("Начнём заново. Выберите режим:", reply_markup=kb_modes()); return

    if data in {"menu_image", "menu_guides", "menu_profile"}:
        await query.message.reply_text("Этот раздел в разработке. Вернёмся к созданию видео?", reply_markup=kb_modes()); return

    await query.message.reply_text(f"Кнопка нажата: {data}")

# ──────────────────────────────────────────────────────────────────────────────
# Точка входа
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        env_path = Path(__file__).with_name(".env")
        raise RuntimeError(f"ENV TELEGRAM_TOKEN не задан. Проверь файл {env_path} и строку TELEGRAM_TOKEN=...")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

