import os
import random
import logging
import asyncio
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from openai import OpenAI

# Логирование
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("babka-bot")

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# Состояния пользователей
# -------------------------------
user_state = {}

DEFAULT_STYLE = "Кино"

# -------------------------------
# GPT Хелперы
# -------------------------------
def gpt_generate(system: str, user: str, temperature=0.7, max_tokens=300):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("GPT error: %s", e)
        return None

def improve_prompt(user_text: str) -> str:
    sys = (
        "Ты редактор промтов для генерации коротких видео. "
        "Никогда не используй кавычки или тире. "
        "Формулируй именно сцену — что происходит, где и кто, а не чувства. "
        "Делай кратко, но с деталями действия."
    )
    return gpt_generate(sys, user_text) or user_text

def suggest_replica(prompt: str) -> str:
    sys = (
        "Придумай короткую реплику персонажа (4-10 слов) к этой сцене. "
        "Никаких кавычек, только сама фраза."
    )
    return gpt_generate(sys, prompt, temperature=0.9, max_tokens=50)

# -------------------------------
# Клавиатуры
# -------------------------------
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="mode_helper")],
        [InlineKeyboardButton("🤡 Мемный режим", callback_data="mode_meme")],
    ])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="make_absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="make_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="make_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_style")]
    ])

def kb_styles():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Кино", callback_data="style_Кино"),
         InlineKeyboardButton("📺 Документальный", callback_data="style_Док")],
        [InlineKeyboardButton("🎤 ASMR", callback_data="style_ASMR"),
         InlineKeyboardButton("🏷️ Бренд", callback_data="style_Бренд")],
        [InlineKeyboardButton("🎨 Арт / Ретро / ЧБ", callback_data="style_Арт"),
         InlineKeyboardButton("🤖 Киберпанк", callback_data="style_Киберпанк")],
        [InlineKeyboardButton("✨ Pixar", callback_data="style_Pixar"),
         InlineKeyboardButton("✏️ Другой стиль", callback_data="style_custom")],
        [InlineKeyboardButton("🚀 Без стиля — генерировать", callback_data="style_None")],
    ])

def kb_after_style():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="add_replica")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")]
    ])

def kb_meme():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить ещё", callback_data="meme_again")],
        [InlineKeyboardButton("🧠✨ Улучшить с помощником", callback_data="meme_to_helper")],
        [InlineKeyboardButton("🎨 Выбрать стиль", callback_data="go_style")]
    ])

# -------------------------------
# Мемный режим — генератор
# -------------------------------
def generate_meme_scene():
    babki = ["Бабка", "Старушка", "Бабуля"]
    животные = ["на носороге", "с капибарой", "с динозавром", "на страусе"]
    локации = ["в деревне", "на стадионе", "в аквапарке", "у подъезда", "на рынке"]
    действия = ["кричит на соседей", "гонит куриц", "поёт частушки", "прыгает в бассейн"]

    return f"{random.choice(babki)} {random.choice(животные)} {random.choice(локации)} {random.choice(действия)}"

# -------------------------------
# Хэндлеры
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_user.id] = {}
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_main())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = user_state.setdefault(uid, {})

    # --- Режимы
    if q.data == "mode_helper":
        st.clear()
        st["mode"] = "helper"
        await q.message.reply_text("🧠✨ Опиши сцену — я помогу улучшить детали.")

    if q.data == "mode_meme":
        st.clear()
        st["mode"] = "meme"
        scene = generate_meme_scene()
        st["prompt"] = scene
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{scene}", reply_markup=kb_meme())

    # --- Варианты GPT
    if q.data in ["make_absurd", "make_simple", "make_again"]:
        base = st.get("prompt", "")
        if not base:
            await q.message.reply_text("Сначала введи сцену.")
            return
        if q.data == "make_absurd":
            new = gpt_generate("Сделай сцену более абсурдной.", base)
        elif q.data == "make_simple":
            new = gpt_generate("Сделай сцену проще и короче.", base)
        else:
            new = improve_prompt(base)
        st["prompt"] = new
        await q.message.reply_text(f"✏️ Вариант:\n\n{new}", reply_markup=kb_variants())

    # --- Переход к стилям
    if q.data == "go_style":
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles())

    # --- Стили
    if q.data.startswith("style_"):
        style = q.data.split("_", 1)[1]
        if style == "custom":
            st["awaiting_custom_style"] = True
            await q.message.reply_text("Введи свой стиль текстом:")
        else:
            st["style"] = None if style == "None" else style
            await q.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
            await q.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())

    # --- Реплика
    if q.data == "add_replica":
        prompt = st.get("prompt")
        if not prompt:
            await q.message.reply_text("Сначала опиши сцену.")
            return
        repl = suggest_replica(prompt)
        st["replica"] = repl
        await q.message.reply_text(f"💬 Реплика предложена: {repl}")
        await q.message.reply_text("Готово! Можно генерировать.", reply_markup=kb_after_style())

    # --- Мемный режим
    if q.data == "meme_again":
        scene = generate_meme_scene()
        st["prompt"] = scene
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{scene}", reply_markup=kb_meme())

    if q.data == "meme_to_helper":
        base = st.get("prompt", "")
        if base:
            new = improve_prompt(base)
            st["prompt"] = new
            await q.message.reply_text(f"🧠✨ Улучшено:\n\n{new}", reply_markup=kb_variants())

    # --- Генерация видео (заглушка)
    if q.data == "generate_now":
        await q.message.reply_text("⏳ Генерирую видео...")
        # здесь будет вызов Veo
        await asyncio.sleep(2)  # имитация
        await q.message.reply_text("✅ Видео готово!")

# -------------------------------
# Обработка текста
# -------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = user_state.setdefault(uid, {})

    if st.get("awaiting_custom_style"):
        st["style"] = update.message.text.strip()
        st["awaiting_custom_style"] = False
        await update.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
        await update.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())
        return

    if st.get("mode") == "helper":
        scene = improve_prompt(update.message.text)
        st["prompt"] = scene
        await update.message.reply_text(f"📝 Промт улучшен:\n\n{scene}", reply_markup=kb_variants())
        return

# -------------------------------
# Запуск
# -------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()

