# -*- coding: utf-8 -*-
"""
Бабка Бот — сценариcт для коротких видео

Особенности:
- Стартовое меню (как на скринах).
- Генерация через GPT (gpt-4o-mini по умолчанию).
- Режимы: Умный помощник, Я сам напишу промт, Мемный режим, Как у NEUROKUDO.
- Как у NEUROKUDO: подрежимы (Обычная 8 сек / Репортаж / Две сцены по 8 сек),
  сразу добавляется реплика, есть кнопка "Поменять реплику".
- Кнопки "Абсурднее / Проще", "Заново", "Далее", "Выбрать стиль".
- После выбора стиля — клавиатура скрывается, остаётся подтверждение.
- Жёсткий запрет тире и кавычек (санитайзер + системные подсказки).
- История в data/history.jsonl.
- Болтовня вне сценариев ограничена (чтобы не сжигать токены).

Зависимости (requirements.txt):
python-telegram-bot==20.6
openai>=1.40.0
python-dotenv==1.0.1
"""

import os
import json
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# -----------------------------------------------------------------------------
# Конфиг
# -----------------------------------------------------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_PATH = DATA_DIR / "history.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
)
log = logging.getLogger("babka-bot")

if not BOT_TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY не задан — GPT работать не будет.")

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------------------------------------------------------
# Вспомогалки
# -----------------------------------------------------------------------------
def ts() -> str:
    return datetime.utcnow().isoformat()


def sanitize_text(text: str) -> str:
    """Запрет тире и кавычек, чистка мусора, один пробел."""
    bad = "-–—-−\"'“”„«»"
    for ch in bad:
        text = text.replace(ch, "")
    return " ".join(text.split()).strip()


def save_history(rec: Dict[str, Any]) -> None:
    rec["time"] = ts()
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_history(limit: int = 15, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    items: List[Dict[str, Any]] = []
    with HISTORY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                if user_id is None or row.get("user_id") == user_id:
                    items.append(row)
            except Exception:
                continue
    items.sort(key=lambda x: x.get("time", ""), reverse=True)
    return items[:limit]


async def gpt_chat(system: str, user: str, temperature: float = 0.8, max_tokens: int = 700) -> str:
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sanitize_text(system)},
                {"role": "user", "content": sanitize_text(user)},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = resp.choices[0].message.content or ""
        return sanitize_text(out)
    except Exception as e:
        log.error("OpenAI error: %s", e)
        return "Помощник временно недоступен"

# -----------------------------------------------------------------------------
# Состояние
# -----------------------------------------------------------------------------
STATE: Dict[int, Dict[str, Any]] = {}


def st(uid: int) -> Dict[str, Any]:
    if uid not in STATE:
        STATE[uid] = {
            "mode": None,         # helper | manual | mem | nk
            "nk_mode": None,      # simple | report | dual
            "idea": None,
            "scene": None,
            "replica": None,
            "style": None,
            "final": None,
        }
    return STATE[uid]

# -----------------------------------------------------------------------------
# Меню и клавиатуры
# -----------------------------------------------------------------------------
# Главное меню (как на скринах)
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Создание видео с помощником")],
        [KeyboardButton("🖼️ Оживление изображения")],
        [KeyboardButton("📚 Гайды / Оплата")],
        [KeyboardButton("👤 Профиль / Баланс")],
    ],
    resize_keyboard=True,
)

def kb_generation_modes() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="gen|helper")],
        [InlineKeyboardButton("🔮 Как у NEUROKUDO",  callback_data="nk|menu")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="gen|manual")],
        [InlineKeyboardButton("🎲 Мемный режим",       callback_data="gen|mem")],
        [InlineKeyboardButton("⬅️ Назад в меню",        callback_data="nav|menu")],
    ])

STYLE_OPTIONS = [
    "Кино", "Документальный", "ASMR", "Бренд",
    "Арт / Ретро / ЧБ", "Киберпанк", "Pixar", "Другой стиль",
    "Без стиля — генерировать",
]

def kb_styles() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, s in enumerate(STYLE_OPTIONS, start=1):
        row.append(InlineKeyboardButton(s, callback_data=f"style|{s}"))
        if i % 2 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="nav|menu")])
    return InlineKeyboardMarkup(rows)

def kb_after_scene_common() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="refine|absurd"),
         InlineKeyboardButton("🎯 Проще",     callback_data="refine|simple")],
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="replica|gen")],
        [InlineKeyboardButton("➡️ Далее", callback_data="flow|to_style")],
        [InlineKeyboardButton("🔄 Заново", callback_data="flow|reset")],
    ])

def kb_post_style_common() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="replica|gen")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="go|gen")],
    ])

# NEUROKUDO — внутри раздела используем 🧪
NK_EMOJI_INTERNAL = "🧪"

def kb_nk_mode() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Обычная сцена 8 сек", callback_data="nk|choose|simple")],
        [InlineKeyboardButton("📰 Репортаж",            callback_data="nk|choose|report")],
        [InlineKeyboardButton("🎥 Две сцены по 8 сек",  callback_data="nk|choose|dual")],
        [InlineKeyboardButton("⬅️ В меню",              callback_data="nav|menu")],
    ])

def kb_after_scene_nk() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="nk|refine|absurd"),
         InlineKeyboardButton("🎯 Проще",     callback_data="nk|refine|simple")],
        [InlineKeyboardButton("💬 Поменять реплику", callback_data="nk|replica|change")],
        [InlineKeyboardButton("🔄 Заново", callback_data="nk|again|same")],
        [InlineKeyboardButton("🎨 Выбрать стиль", callback_data="flow|to_style")],
    ])

def kb_post_style_nk() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Поменять реплику", callback_data="nk|replica|change")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="go|gen")],
    ])

# -----------------------------------------------------------------------------
# Системные подсказки для GPT
# -----------------------------------------------------------------------------
SYSTEM_COMMON = sanitize_text("""
Ты сценарный помощник. Пиши кратко, по делу, без поэзии и эмоций.
Строго запрещены тире и любые кавычки.
Всегда держись тайминга: максимум два плана, суммарно около восьми секунд.
Верни строго структуру: Заголовок; Сцена (или План 1/План 2); Реплика если попросили.
""")

SYSTEM_ASSIST_REFINE = sanitize_text("""
Ты редактор сцены. Сохраняй ту же структуру блоков.
Режим "абсурднее" повышает неожиданность, но логика сохраняется.
Режим "проще" делает понятнее, короче, приземлённее.
Запрещены тире и любые кавычки.
""")

def _nk_base_style() -> str:
    return sanitize_text("""
Ты создаёшь сцены в стиле Neurokudo. Пиши очень кратко и предметно.
Запрещены тире и кавычки. Камера с плеча, документальная подача.
Маркиры: деревенский двор, покосившийся забор, собаки лают вдали,
розовый надувной фламинго, голубой кафельный бассейн в русском дворе.
Репортёр говорит официально и сухо; герой — народно и живо.
Всегда добавляй блок Реплика героя.
""")

def _nk_mode_instructions(mode: str) -> str:
    if mode == "simple":
        return sanitize_text("Одна сцена примерно восемь секунд. Блоки: Заголовок; Сцена; Реплика.")
    if mode == "dual":
        return sanitize_text("Две сцены по восемь секунд. Блоки: Заголовок; План 1; План 2; Реплика.")
    if mode == "report":
        return sanitize_text("Репортаж. Блоки: Заголовок; Репортаж; Кадры; Реплика.")
    return ""

def NK_SYSTEM(mode: str) -> str:
    return _nk_base_style() + " " + _nk_mode_instructions(mode)

# -----------------------------------------------------------------------------
# Команды
# -----------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    STATE.pop(uid, None)
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=MAIN_MENU)
    await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я помогу придумать короткую сцену для видео. "
        "Всегда держимся двух планов и коротких формулировок.",
        reply_markup=MAIN_MENU,
    )

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = load_history(20, uid)
    if not items:
        await update.message.reply_text("История пуста.", reply_markup=MAIN_MENU)
        return
    lines = []
    for i, it in enumerate(items, start=1):
        title = (it.get("scene") or "").split("\n", 1)[0][:60]
        style = it.get("style") or "без стиля"
        lines.append(f"{i}. {title}  стиль {style}")
    await update.message.reply_text("Последние промты:\n" + "\n".join(lines), reply_markup=MAIN_MENU)

# -----------------------------------------------------------------------------
# Текстовый роутер (минимум болтовни)
# -----------------------------------------------------------------------------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (update.message.text or "").strip()
    uid = update.effective_user.id
    s = st(uid)

    # Главное меню
    if msg == "🎬 Создание видео с помощником":
        await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes())
        return
    if msg == "🖼️ Оживление изображения":
        await update.message.reply_text("Этот раздел скоро включим. Выберите другой режим.", reply_markup=MAIN_MENU)
        return
    if msg == "📚 Гайды / Оплата":
        await update.message.reply_text("Гайды и оплата — скоро. Пока пользуйтесь режимами генерации.", reply_markup=MAIN_MENU)
        return
    if msg == "👤 Профиль / Баланс":
        await update.message.reply_text("Профиль и баланс — скоро.", reply_markup=MAIN_MENU)
        return

    # Внутренние режимы
    if s.get("mode") == "helper":
        s["idea"] = msg
        await propose_scene_helper(update, context, uid)
        return
    if s.get("mode") == "manual":
        # Сохраняем как есть, без правок
        s["scene"] = f"Промт без изменений:\n{msg}"
        await update.message.reply_text(s["scene"], reply_markup=kb_after_scene_common())
        return
    if s.get("mode") == "nk":
        # В NK болтовню режем — только кнопки
        await update.message.reply_text("Здесь свободный ввод отключён. Используйте кнопки над чатом.")
        return

    # Остальное — в меню
    await update.message.reply_text("Выберите пункт меню ниже ⬇️", reply_markup=MAIN_MENU)

# -----------------------------------------------------------------------------
# Логика режимов
# -----------------------------------------------------------------------------
# ---- Умный помощник
async def propose_scene_helper(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = st(uid)
    idea = s.get("idea") or "Придумай простую сцену"
    prompt = f"Сформулируй лаконичную съёмочную сцену по идее: {idea}. Верни Заголовок; Сцена."
    text = await gpt_chat(SYSTEM_COMMON, prompt)
    s["scene"] = text
    await update.message.reply_text(f"🧠✨ Улучшено помощником:\n{text}", reply_markup=kb_after_scene_common())

# ---- Мемный режим (укороченные списки, чаще смешно)
MEM_SUBJECTS = ["Бабка", "Дед", "Повар", "Дворник", "Курьер", "Футболист", "Гламурная девица", "Капибара"]
MEM_ACTIONS  = ["едет верхом", "танцует", "спорит", "машет руками", "прыгает в лужу", "вытаскивает арбуз"]
MEM_OBJECTS  = ["на свинье", "с самоваром", "с портретом Ленина", "с надувным фламинго", "с голубым тазом"]
MEM_LOCS     = ["в деревне", "на стадионе", "у бассейна", "на стройке", "во дворе", "у сельсовета"]

async def mem_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = st(uid)
    s["mode"] = "mem"
    idea = f"{random.choice(MEM_SUBJECTS)} {random.choice(MEM_ACTIONS)} {random.choice(MEM_OBJECTS)} {random.choice(MEM_LOCS)}"
    s["idea"] = idea
    prompt = f"Сделай короткую смешную сцену из двух планов по восемь секунд. Идея: {idea}. Верни Заголовок; Сцена 1; Сцена 2."
    text = await gpt_chat(SYSTEM_COMMON, prompt)
    s["scene"] = text
    await update.effective_message.reply_text(f"🎭 Мемная сцена:\n{text}", reply_markup=kb_after_scene_common())

# ---- NEUROKUDO
NK_ABOUT = (
    f"{NK_EMOJI_INTERNAL} Режим 'Как у NEUROKUDO'. "
    "Соберём сцену в фирменном стиле. Выбери подрежим:"
)

async def nk_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, mode: str):
    s = st(uid)
    s["mode"] = "nk"
    s["nk_mode"] = mode
    text = await gpt_chat(NK_SYSTEM(mode), "Сгенерируй сцену строго в стиле Neurokudo.")
    s["scene"] = text
    # Реплика уже присутствует в тексте — кнопка "Поменять реплику"
    await update.effective_message.reply_text(f"{NK_EMOJI_INTERNAL} Готово:\n{text}", reply_markup=kb_after_scene_nk())

async def nk_refine(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, how: str):
    s = st(uid)
    base = s.get("scene") or ""
    tweak = "Усиль абсурд, но оставь логику и краткость." if how == "absurd" \
            else "Сделай проще и короче, понятнее массовой аудитории."
    text = await gpt_chat(NK_SYSTEM(s.get("nk_mode") or "simple"), base + " " + tweak + " Верни ту же структуру.")
    s["scene"] = text
    await update.effective_message.edit_text(text, reply_markup=kb_after_scene_nk())

async def nk_change_replica(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = st(uid)
    base = s.get("scene") or ""
    ask = "По этой сцене предложи другую короткую народную реплику героя. Одна строка без кавычек и тире."
    rep = await gpt_chat(NK_SYSTEM(s.get("nk_mode") or "simple"), base + " " + ask)
    s["replica"] = rep
    await update.effective_message.reply_text(f"Новая реплика:\n{rep}")

async def nk_again(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    mode = st(uid).get("nk_mode") or "simple"
    await update.callback_query.edit_message_text("Генерирую заново…")
    await nk_generate(update, context, uid, mode)

# -----------------------------------------------------------------------------
# Стиль, реплики, финал
# -----------------------------------------------------------------------------
def assemble_final(uid: int) -> str:
    s = st(uid)
    scene = s.get("scene") or ""
    style = s.get("style") or "без стиля"
    rep = s.get("replica")
    block = scene
    if rep:
        block += f"\nРеплика\n{rep}"
    final = f"{block}\n\nСтиль\n{style}\nТайминг шестнадцать секунд, две сцены по восемь."
    return sanitize_text(final)

async def on_choose_style(qmsg, uid: int, style: str):
    s = st(uid)
    s["style"] = style
    await qmsg.edit_message_text(f"🎨 Стиль выбран: {style}")
    # После выбора стиля — разные кнопки для NK и остальных
    if s.get("mode") == "nk":
        await qmsg.message.reply_text("Теперь можно поменять реплику или сразу сгенерировать.", reply_markup=kb_post_style_nk())
    else:
        await qmsg.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_post_style_common())

async def generate_replica(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = st(uid)
    base = s.get("scene") or ""
    text = await gpt_chat(SYSTEM_COMMON, f"{base}\nПредложи короткую народную реплику героя. Одна строка.")
    s["replica"] = text
    await update.effective_message.reply_text(f"Реплика предложена:\n{text}")

# Имитация генерации видео (без Veo), плюс сохраняем историю
async def go_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = st(uid)
    final = assemble_final(uid)
    s["final"] = final

    # Сохраняем в историю
    save_history({
        "user_id": uid,
        "scene": s.get("scene"),
        "style": s.get("style"),
        "replica": s.get("replica"),
        "final": final,
    })

    await update.effective_message.reply_text("⏳ Генерирую видео…")
    await update.effective_message.reply_text("✅ Видео готово! (пока отправляю текст-подсказку для Veo)")
    await update.effective_message.reply_text(final)

# -----------------------------------------------------------------------------
# CallbackQuery роутер
# -----------------------------------------------------------------------------
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    data = (q.data or "")
    parts = data.split("|")
    kind = parts[0]
    rest = parts[1:]

    # Навигация
    if kind == "nav":
        where = rest[0] if rest else "menu"
        await q.edit_message_text("Меню")
        await q.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes())
        return

    # Генерация: выбор режима
    if kind == "gen":
        action = rest[0] if rest else ""
        if action == "helper":
            st(uid).update({"mode": "helper", "idea": None, "scene": None, "style": None, "replica": None})
            await q.edit_message_text("🧠✨ Опиши сцену — сделаю её съёмочной на ~8 секунд.")
            return
        if action == "manual":
            st(uid).update({"mode": "manual", "scene": None, "style": None, "replica": None})
            await q.edit_message_text("Напишите промт одной строкой — сохраню без изменений.")
            return
        if action == "mem":
            st(uid).update({"mode": "mem", "scene": None, "style": None, "replica": None})
            await q.edit_message_text("🎲 Кручу мемный режим…")
            await mem_generate(update, context)
            return

    # Помощник: тюнинг / поток
    if kind == "refine":
        how = rest[0] if rest else "simple"
        base = st(uid).get("scene") or ""
        tweak = "Усиль абсурд, но сохрани логику." if how == "absurd" else "Сделай проще, короче и понятнее."
        text = await gpt_chat(SYSTEM_ASSIST_REFINE, base + " " + tweak + " Верни ту же структуру.")
        st(uid)["scene"] = text
        await q.edit_message_text(text, reply_markup=kb_after_scene_common())
        return

    if kind == "flow":
        step = rest[0] if rest else ""
        if step == "to_style":
            await q.edit_message_text("Выбери стиль:")
            await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles())
            return
        if step == "reset":
            # Сбрасываем сцену в текущем режиме
            st(uid)["scene"] = None
            await q.edit_message_text("Сцена сброшена. Опишите новую идею или выберите режим заново.")
            return

    if kind == "replica":
        act = rest[0] if rest else "gen"
        if act == "gen":
            await generate_replica(update, context, uid)
            return

    if kind == "style":
        style = rest[0] if rest else "Без стиля — генерировать"
        await on_choose_style(q, uid, style)
        return

    if kind == "go":
        if (rest[0] if rest else "") == "gen":
            await go_generate(update, context, uid)
            return

    # NEUROKUDO
    if kind == "nk":
        action = rest[0] if rest else ""
        if action == "menu":
            st(uid).update({"mode": "nk", "nk_mode": None, "scene": None, "style": None, "replica": None})
            await q.edit_message_text(NK_ABOUT, reply_markup=kb_nk_mode())
            return
        if action == "choose":
            sub = rest[1] if len(rest) > 1 else "simple"
            await q.edit_message_text(f"{NK_EMOJI_INTERNAL} Генерирую…")
            await nk_generate(update, context, uid, sub)
            return
        if action == "refine":
            how = rest[1] if len(rest) > 1 else "simple"
            await nk_refine(update, context, uid, how)
            return
        if action == "replica" and len(rest) > 1 and rest[1] == "change":
            await nk_change_replica(update, context, uid)
            return
        if action == "again":
            await nk_again(update, context, uid)
            return

# -----------------------------------------------------------------------------
# Инициализация бота
# -----------------------------------------------------------------------------
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app


if __name__ == "__main__":
    log.info(f"GPT модель: {OPENAI_MODEL}")
    app = build_app()
    log.info("Bot is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

