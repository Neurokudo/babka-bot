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

# ──────────────────────────────────────────────────────────────────────────────
# .env грузим из той же папки, где лежит файл
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# ──────────────────────────────────────────────────────────────────────────────
# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("babka-bot")

# ──────────────────────────────────────────────────────────────────────────────
# Состояние
user_state: dict[int, dict] = {}
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "cinema")

def _ensure_state(uid: int):
    if uid not in user_state:
        user_state[uid] = {
            "mode": None,
            "prompt": None,
            "style": None,
            "replica": None,
            "awaiting_replica": False,
            "awaiting_custom_style": False,
        }

# ──────────────────────────────────────────────────────────────────────────────
# Gemini (google-generativeai==0.8.5)
import google.generativeai as genai

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
    log.info("Gemini disabled.")

def suggest_replica(prompt: str) -> str:
    """
    Возвращает короткую смешную реплику персонажа.
    При любой ошибке/пустом ответе вернёт безопасный фолбэк.
    """
    if not gemini_model:
        log.warning("Gemini model is not initialized.")
        return "Ну держитесь теперь!"
    try:
        resp = gemini_model.generate_content(
            contents=(
                "Сделай ОДНУ короткую (до 12 слов) смешную живую реплику персонажа для подписи к видео. "
                "Без кавычек, эмодзи и хештегов, без пояснений. Только фраза.\n"
                f"Контекст сцены: {prompt}"
            ),
            generation_config={
                "max_output_tokens": 32,
                "temperature": 0.9,
                "top_p": 0.95,
            },
        )
        text = (getattr(resp, "text", "") or "").strip()
        if not text:
            log.warning("Gemini returned empty text. candidates=%s", getattr(resp, "candidates", None))
            return "Ну держитесь теперь!"
        return text
    except Exception as e:
        log.exception("Gemini generate_content failed: %s", e)
        return "Ну держитесь теперь!"

# ──────────────────────────────────────────────────────────────────────────────
# Veo client (google-cloud-aiplatform==1.115.0)
# В твоём veo_client.py реализован generate_video_sync(prompt, style, replica, seconds)
from veo_client import generate_video_sync

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
    uid = update.effective_user.id
    _ensure_state(uid)
    await update.message.reply_text("👋 Привет! Я бот для генерации видео.", reply_markup=kb_main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши описание сцены → выбери стиль → нажми «Сгенерировать сейчас». /test_llm — проверка Gemini.")

async def test_llm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = suggest_replica("Бабка едет на осле по деревне; камера низкая, мягкий дневной свет")
    await update.message.reply_text(f"Gemini test → {phrase}")

# ──────────────────────────────────────────────────────────────────────────────
# Генерация видео (через veo_client.generate_video_sync)
async def generate_video(query, context):
    uid = query.from_user.id
    _ensure_state(uid)
    st = user_state[uid]

    prompt = st.get("prompt") or "(пусто)"
    style  = st.get("style") or DEFAULT_STYLE
    replica = st.get("replica")

    await query.message.reply_text("⏳ Генерирую видео в Veo 3… это может занять немного времени.")

    try:
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
# Обработка обычного текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure_state(uid)
    st = user_state[uid]
    text = (update.message.text or "").strip()

    if st.get("awaiting_replica"):
        st["replica"] = text
        st["awaiting_replica"] = False
        await update.message.reply_text(f"✅ Реплика сохранена:\n{text}", reply_markup=kb_after_prompt())
        return

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
    uid = query.from_user.id
    _ensure_state(uid)
    st = user_state[uid]

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
        user_state[uid] = {
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
        raise RuntimeError(f"ENV TELEGRAM_TOKEN не задан. Проверь {env_path} или Railway Variables.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("test_llm", test_llm))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

