# -*- coding: utf-8 -*-
"""
Бабка Бот — генератор коротких сценариев (Telegram)

ENV (как в Railway):
- BOT_TOKEN
- OPENAI_API_KEY
- LLM_PROVIDER (openai)
- OPENAI_MODEL / GENAI_MODEL (если нет — используем gpt-4o)

Модель по умолчанию: gpt-4o
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
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

# -----------------------------------------------------------------------------
# Конфиг
# -----------------------------------------------------------------------------
load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
LLM_PROVIDER    = (os.getenv("LLM_PROVIDER", "openai") or "openai").lower()

# Модель: при openai НЕ читаем GENAI_MODEL вообще
if LLM_PROVIDER == "openai":
    OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o"
    # защита от случайной строки gemini
    if "gemini" in OPENAI_MODEL.lower():
        OPENAI_MODEL = "gpt-4o"
else:
    # для других провайдеров (если появятся)
    OPENAI_MODEL = os.getenv("GENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s: %(message)s")
log = logging.getLogger("babka-bot")

# Инициализация OpenAI клиента
client = OpenAI(api_key=OPENAI_API_KEY)

DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
HISTORY = DATA_DIR / "history.jsonl"

# -----------------------------------------------------------------------------
# Утилиты
# -----------------------------------------------------------------------------
def now_iso() -> str: return datetime.utcnow().isoformat()

def sanitize(text: str) -> str:
    # запрет тире/кавычек для TTS/чистоты
    for ch in "-–—−\"'“”„«»":
        text = text.replace(ch, "")
    return " ".join(text.split()).strip()

def save_history(rec: Dict[str, Any]) -> None:
    rec["time"] = now_iso()
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_history(uid: int, limit: int = 20) -> List[Dict[str, Any]]:
    if not HISTORY.exists(): return []
    out = []
    with HISTORY.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                if row.get("user_id") == uid:
                    out.append(row)
            except Exception:
                pass
    out.sort(key=lambda x: x.get("time",""), reverse=True)
    return out[:limit]

async def gpt(system: str, user: str, temperature: float = 0.8, max_tokens: int = 700) -> str:
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": sanitize(system)},
                      {"role": "user", "content": sanitize(user)}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = resp.choices[0].message.content or ""
        return sanitize(out)
    except Exception as e:
        log.error("OpenAI error: %s", e)
        return "Помощник временно недоступен"

# -----------------------------------------------------------------------------
# Состояние
# -----------------------------------------------------------------------------
STATE: Dict[int, Dict[str, Any]] = {}
def S(uid: int) -> Dict[str, Any]:
    if uid not in STATE:
        STATE[uid] = {
            "mode": None,       # helper | mem | nk | manual
            "nk_mode": None,    # simple | report | dual
            "idea": None,
            "scene": None,      # простые режимы и NK simple/dual
            "style": None,
            "replica": None,
            "final": None,
            # для репортажа
            "nk_report": {
                "lead": None,     # кадр 1 — Вступление (ведущая + факт), фон-действие описывается в той же строке
                "detail": None,   # кадр 2 — Крупный план героя и объекта
                "replica": None   # короткая народная фраза героя
            },
            "await": None,      # ожидание текста пользователя (редактирование)
        }
    return STATE[uid]

# -----------------------------------------------------------------------------
# Клавиатуры
# -----------------------------------------------------------------------------
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Создание видео с помощником")],
        [KeyboardButton("🖼️ Оживление изображения")],
        [KeyboardButton("📚 Гайды / Оплата")],
        [KeyboardButton("👤 Профиль / Баланс")],
    ], resize_keyboard=True
)

def kb_generation_modes() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="gen|helper")],
        [InlineKeyboardButton("🔮 Как у NEUROKUDO", callback_data="nk|menu")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="gen|manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="gen|mem")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="nav|menu")],
    ])

STYLE_OPTIONS = [
    "Кино","Документальный","ASMR","Бренд","Арт / Ретро / ЧБ","Киберпанк","Pixar","Другой стиль","Без стиля — генерировать"
]
def kb_styles() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, s in enumerate(STYLE_OPTIONS, start=1):
        row.append(InlineKeyboardButton(s, callback_data=f"style|{s}"))
        if i % 2 == 0: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="nav|menu")])
    return InlineKeyboardMarkup(rows)

def kb_after_scene_common() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="refine|absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="refine|simple")],
        [InlineKeyboardButton("💬 Помощник, предложи своё!", callback_data="helper|suggest")],
        [InlineKeyboardButton("➡️ Далее", callback_data="flow|to_style")],
        [InlineKeyboardButton("🔄 Заново", callback_data="flow|reset")],
    ])

def kb_post_style_common() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="replica|gen")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="go|gen")],
    ])

# NK подрежимы
def kb_nk_mode() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Обычная 8 секунд", callback_data="nk|choose|simple")],
        [InlineKeyboardButton("🎤 Репортаж", callback_data="nk|choose|report")],
        [InlineKeyboardButton("🎞️ Две сцены по 8 секунд", callback_data="nk|choose|dual")],
        [InlineKeyboardButton("⬅️ В меню", callback_data="nav|menu")],
    ])

def kb_after_scene_nk() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="nk|refine|absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="nk|refine|simple")],
        [InlineKeyboardButton("💬 Поменять реплику", callback_data="nk|replica|change")],
        [InlineKeyboardButton("🔄 Заново", callback_data="nk|again|same")],
        [InlineKeyboardButton("🎨 Выбрать стиль", callback_data="flow|to_style")],
    ])

def kb_post_style_nk() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Поменять реплику", callback_data="nk|replica|change")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="go|gen")],
    ])

# NK репортаж — клавиатура после превью двух кадров
def kb_after_report() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Править кадр 1", callback_data="nk|report|edit|lead"),
         InlineKeyboardButton("✏️ Править кадр 2", callback_data="nk|report|edit|detail")],
        [InlineKeyboardButton("💬 Поменять реплику", callback_data="nk|report|replica")],
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="nk|report|refine|absurd"),
         InlineKeyboardButton("🎯 Проще",    callback_data="nk|report|refine|simple")],
        [InlineKeyboardButton("🎨 Выбрать стиль", callback_data="flow|to_style")],
        [InlineKeyboardButton("🔄 Заново", callback_data="nk|again|same")],
    ])

# -----------------------------------------------------------------------------
# Системные подсказки
# -----------------------------------------------------------------------------
SYSTEM_COMMON = sanitize("""
Ты сценарный ассистент. Пиши кратко и по делу. Никакой поэзии и эмоций.
Строго запрещены тире и любые кавычки.
Сцена должна укладываться примерно в восемь секунд, максимум два плана.
Всегда возвращай понятную структуру: Заголовок; Сцена; при необходимости План 1/План 2; и Реплика если попросят.
""")

SYSTEM_ASSIST_REFINE = sanitize("""
Редактор сцены. Сохраняй структуру. Абсурднее — чуть безумней, но логично. Проще — короче и понятнее.
Запрещены тире и кавычки. Тайминг до восьми секунд, не более двух планов.
""")

def NK_SYSTEM(mode: str) -> str:
    base = sanitize("""
Стиль Neurokudo: документальная подача, камера с плеча, коротко и утилитарно.
Реквизит и места часто: розовый надувной фламинго, голубой кафельный бассейн в деревенском дворе,
покосившийся забор, подъезд, сельский магазин, дворики, площадки.
Запрещены тире и кавычки. Пиши просто, без поэзии. Всегда дай короткую народную реплику героя.
""")
    if mode == "simple":
        mode_txt = "Одна сцена около восьми секунд. Блоки: Заголовок; Сцена; Реплика."
    elif mode == "dual":
        mode_txt = "Две сцены по восемь секунд. Блоки: Заголовок; План 1; План 2; Реплика."
    else:
        # репортаж: два коротких кадра суммарно ~8 сек
        mode_txt = sanitize("""
Репортаж из двух кадров суммарно около восьми секунд.
Верни аккуратные блоки:
Вступление  текст ведущей одной строкой про факт события  на фоне видно действие с объектом и героем
Крупный план  крупно герой и объект  одно короткое описание
Реплика  короткая народная фраза героя
Без кавычек и тире. Коротко и утилитарно.
""")
    return base + " " + mode_txt

# -----------------------------------------------------------------------------
# Команды
# -----------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    STATE.pop(uid, None)
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=MAIN_MENU)
    await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я помогу придумать короткую сцену. Выберите режим ниже.", reply_markup=MAIN_MENU)

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = load_history(uid, 15)
    if not items:
        await update.message.reply_text("История пуста.", reply_markup=MAIN_MENU); return
    msg = "Последние промты:\n" + "\n".join(
        f"{i+1}. {(it.get('scene') or '').splitlines()[0][:60]}  стиль: {it.get('style') or 'нет'}"
        for i, it in enumerate(items)
    )
    await update.message.reply_text(msg, reply_markup=MAIN_MENU)

# -----------------------------------------------------------------------------
# Роутер текста (режем болтовню)
# -----------------------------------------------------------------------------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = (update.message.text or "").strip()
    state = S(uid)

    # ожидание текстовых правок для репортажа
    if state.get("await"):
        tag = state["await"]; state["await"] = None
        if tag in ("nk_report_edit_lead", "nk_report_edit_detail"):
            part = "lead" if tag.endswith("lead") else "detail"
            await nk_report_apply_edit(update, context, uid, part, txt)
            return

    # Главное меню
    if txt == "🎬 Создание видео с помощником":
        await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes()); return
    if txt == "🖼️ Оживление изображения":
        await update.message.reply_text("Этот раздел скоро включим. Выберите другой режим.", reply_markup=MAIN_MENU); return
    if txt == "📚 Гайды / Оплата":
        await update.message.reply_text("Гайды и оплата — скоро. А пока — генерация сцен!", reply_markup=MAIN_MENU); return
    if txt == "👤 Профиль / Баланс":
        await update.message.reply_text("Профиль и баланс — скоро.", reply_markup=MAIN_MENU); return

    # Контекстные режимы
    if state.get("mode") == "helper":
        state["idea"] = txt
        await propose_scene_helper(update, context, uid)
        return
    if state.get("mode") == "manual":
        state["scene"] = f"Промт без изменений:\n{txt}"
        await update.message.reply_text(state["scene"], reply_markup=kb_after_scene_common())
        return
    if state.get("mode") == "nk":
        await update.message.reply_text("В этом разделе свободный чат отключён. Жмите кнопки над чатом.")
        return

    await update.message.reply_text("Выберите пункт меню ниже ⬇️", reply_markup=MAIN_MENU)

# -----------------------------------------------------------------------------
# Режимы
# -----------------------------------------------------------------------------
# 1) Умный помощник
async def propose_scene_helper(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid)
    idea = s.get("idea") or "Придумай простую сцену"
    prompt = f"Сформулируй лаконичную съёмочную сцену по идее: {idea}. Верни блоки Заголовок; Сцена. Тайминг около восьми секунд, максимум два плана."
    text = await gpt(SYSTEM_COMMON, prompt)
    s["scene"] = text
    await update.message.reply_text(f"🧠✨ Улучшено помощником:\n{text}", reply_markup=kb_after_scene_common())

# 2) Мемный режим (укороченные списки — чаще смешно)
MEM_SUBJECTS = ["Бабка","Дед","Повар","Дворник","Курьер","Футболист","Гламурная девица","Капибара"]
MEM_ACTIONS  = ["едет верхом","танцует","спорит","машет руками","прыгает в лужу","вытаскивает арбуз"]
MEM_OBJECTS  = ["на свинье","с самоваром","с портретом Ленина","с надувным фламинго","с голубым тазом"]
MEM_LOCS     = ["в деревне","на стадионе","у бассейна","на стройке","во дворе","у сельсовета"]

async def mem_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = S(uid); s["mode"] = "mem"; s["style"] = None; s["replica"] = None
    idea = f"{random.choice(MEM_SUBJECTS)} {random.choice(MEM_ACTIONS)} {random.choice(MEM_OBJECTS)} {random.choice(MEM_LOCS)}"
    s["idea"] = idea
    text = await gpt(
        SYSTEM_COMMON,
        f"Сделай короткую смешную сцену. Идея: {idea}. Верни Заголовок; Сцена или два плана. Тайминг около восьми секунд."
    )
    s["scene"] = text
    await update.effective_message.reply_text(f"🎭 Мемная сцена:\n{text}", reply_markup=kb_after_scene_common())

# 3) Как у NEUROKUDO — simple/dual
async def nk_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, mode: str):
    s = S(uid); s["mode"] = "nk"; s["nk_mode"] = mode; s["style"] = None; s["replica"] = None
    txt = await gpt(NK_SYSTEM(mode), "Сгенерируй сцену строго в стиле Neurokudo.")
    s["scene"] = txt
    await update.effective_message.reply_text(f"🧪 Готово:\n{txt}", reply_markup=kb_after_scene_nk())

async def nk_refine(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, how: str):
    s = S(uid)
    tweak = "Усиль абсурд, но сохрани логику и краткость." if how == "absurd" else "Сделай проще и короче."
    txt = await gpt(NK_SYSTEM(s.get("nk_mode") or "simple"), (s.get("scene") or "") + " " + tweak + " Верни ту же структуру.")
    s["scene"] = txt
    await update.effective_message.edit_text(txt, reply_markup=kb_after_scene_nk())

async def nk_change_replica(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid)
    ask = "По этой сцене предложи другую короткую народную реплику героя. Одна строка."
    rep = await gpt(NK_SYSTEM(s.get("nk_mode") or "simple"), (s.get("scene") or "") + " " + ask)
    s["replica"] = rep
    await update.effective_message.reply_text(f"Новая реплика:\n{rep}")

async def nk_again(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    mode = S(uid).get("nk_mode") or "simple"
    await update.callback_query.edit_message_text("Генерирую заново…")
    if mode == "report":
        await nk_report_generate(update, context, uid)
    else:
        await nk_generate(update, context, uid, mode)

# 3b) Как у NEUROKUDO — РЕПОРТАЖ (два кадра)
async def nk_report_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid); s["mode"]="nk"; s["nk_mode"]="report"; s["style"]=None; s["replica"]=None
    sys = NK_SYSTEM("report")
    txt = await gpt(sys, "Сгенерируй репортаж из двух кадров как описано.")
    # пытаемся распарсить по ключевым заголовкам
    lead = detail = replica = ""
    for line in txt.splitlines():
        l = line.strip()
        low = l.lower()
        if low.startswith("вступление"):
            lead = l.split(" ", 1)[-1].strip()
        elif low.startswith("крупный план"):
            detail = l.split(" ", 2)[-1].strip()
        elif low.startswith("реплика"):
            replica = l.split(" ", 1)[-1].strip()
    if not (lead and detail):
        # жёсткая перегенерация с требованием заголовков
        txt2 = await gpt(sys, "Повтори строго с заголовками строк Вступление Крупный план Реплика")
        lead = detail = replica = ""
        for line in txt2.splitlines():
            l = line.strip(); low = l.lower()
            if low.startswith("вступление"):
                lead = l.split(" ", 1)[-1].strip()
            elif low.startswith("крупный план"):
                detail = l.split(" ", 2)[-1].strip()
            elif low.startswith("реплика"):
                replica = l.split(" ", 1)[-1].strip()
    s["nk_report"].update({"lead": lead, "detail": detail, "replica": replica})
    await nk_report_preview(update, uid)

def nk_report_preview_text(uid: int) -> str:
    r = S(uid)["nk_report"]
    return (
        "🎙️ Вступление:\n" + (r.get("lead") or "") +
        "\n\n🎬 Крупный план:\n" + (r.get("detail") or "") +
        ("\n\n💬 Реплика:\n" + r.get("replica") if r.get("replica") else "")
    )

async def nk_report_preview(update: Update, uid: int):
    await update.effective_message.reply_text(
        nk_report_preview_text(uid),
        reply_markup=kb_after_report()
    )

async def nk_report_edit_ask(update: Update, uid: int, part: str):
    S(uid)["await"] = f"nk_report_edit_{part}"
    label = "кадр 1" if part == "lead" else "кадр 2"
    await update.effective_message.reply_text(
        f"Коротко напишите, что поправить в {label}  например место, действие, ракурс."
    )

async def nk_report_apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, part: str, note: str):
    s = S(uid); r = s["nk_report"]; sys = NK_SYSTEM("report")
    base = r.get(part) or ""
    ask = f"Это фрагмент {part}. Перепиши коротко по замечанию: {note}. Сохрани стиль и структуру репортажа."
    new_piece = await gpt(sys, base + " " + ask)
    r[part] = new_piece
    await update.message.reply_text("Готово. Новая версия:")
    await nk_report_preview(update, uid)

async def nk_report_change_replica(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid); sys = NK_SYSTEM("report")
    scene_txt = nk_report_preview_text(uid)
    rep = await gpt(sys, scene_txt + " Предложи другую короткую народную реплику одной строкой.")
    s["nk_report"]["replica"] = rep
    await update.effective_message.reply_text("Новая реплика:\n" + rep)
    await nk_report_preview(update, uid)

async def nk_report_refine(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, how: str):
    sys = NK_SYSTEM("report")
    tweak = "Сделай чуть безумнее, но логично." if how=="absurd" else "Сделай проще и короче."
    txt = await gpt(sys, nk_report_preview_text(uid) + " " + tweak + " Сохрани два кадра и реплику.")
    # повторный парсинг
    lead = detail = replica = ""
    for line in txt.splitlines():
        l = line.strip(); low = l.lower()
        if low.startswith("вступление"):
            lead = l.split(" ", 1)[-1].strip()
        elif low.startswith("крупный план"):
            detail = l.split(" ", 2)[-1].strip()
        elif low.startswith("реплика"):
            replica = l.split(" ", 1)[-1].strip()
    s = S(uid)
    s["nk_report"].update({"lead": lead or s["nk_report"]["lead"],
                           "detail": detail or s["nk_report"]["detail"],
                           "replica": replica or s["nk_report"]["replica"]})
    await nk_report_preview(update, uid)

# -----------------------------------------------------------------------------
# Поток: стиль / реплика / финал
# -----------------------------------------------------------------------------
def assemble_final(uid: int) -> str:
    s = S(uid)
    if s.get("nk_mode") == "report":
        r = s["nk_report"]
        style = s.get("style") or "без стиля"
        final = (
            "Вступление\n" + (r.get("lead") or "") +
            "\nКрупный план\n" + (r.get("detail") or "") +
            ("\nРеплика\n" + r.get("replica") if r.get("replica") else "")
        )
        final += f"\n\nСтиль\n{style}\nТайминг восемь секунд суммарно два коротких кадра."
        return sanitize(final)
    # остальные режимы как были
    scene = s.get("scene") or ""
    style = s.get("style") or "без стиля"
    rep = s.get("replica")
    final = scene
    if rep: final += f"\nРеплика\n{rep}"
    final += f"\n\nСтиль\n{style}\nТайминг шестнадцать секунд, две сцены по восемь."
    return sanitize(final)

async def on_choose_style(cbq, uid: int, style: str):
    s = S(uid); s["style"] = style
    await cbq.edit_message_text(f"🎨 Стиль выбран: {style}")
    if s.get("nk_mode") == "report":
        await cbq.message.reply_text("Теперь можно поменять реплику или сразу сгенерировать.", reply_markup=kb_post_style_nk())
    elif s.get("mode") == "nk":
        await cbq.message.reply_text("Теперь можно поменять реплику или сразу сгенерировать.", reply_markup=kb_post_style_nk())
    else:
        await cbq.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_post_style_common())

async def generate_replica(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid)
    txt = await gpt(SYSTEM_COMMON, (s.get("scene") or "") + "\nПредложи короткую народную реплику героя. Одна строка.")
    s["replica"] = txt
    await update.effective_message.reply_text(f"Реплика предложена:\n{txt}")

async def go_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    s = S(uid)
    final = assemble_final(uid); s["final"] = final
    save_history({"user_id": uid, "scene": s.get("scene"), "style": s.get("style"),
                  "replica": s.get("replica") or s.get("nk_report",{}).get("replica"), "final": final})
    await update.effective_message.reply_text("⏳ Генерирую видео…")
    # Здесь можно подключить реальную генерацию (VEO) при необходимости
    await update.effective_message.reply_text("✅ Видео готово! (пока отправляю текст-подсказку для Veo)")
    await update.effective_message.reply_text(final)

# -----------------------------------------------------------------------------
# CallbackQuery роутер
# -----------------------------------------------------------------------------
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = update.effective_user.id
    data = (q.data or "")
    parts = data.split("|"); kind = parts[0]; rest = parts[1:]

    # Навигация
    if kind == "nav":
        await q.edit_message_text("Меню")
        await q.message.reply_text("Выберите режим генерации:", reply_markup=kb_generation_modes())
        return

    # Режимы
    if kind == "gen":
        act = rest[0]
        if act == "helper":
            S(uid).update({"mode":"helper","idea":None,"scene":None,"style":None,"replica":None})
            await q.edit_message_text("🧠✨ Опиши сцену — сделаю её съёмочной на ~8 секунд.")
            return
        if act == "manual":
            S(uid).update({"mode":"manual","scene":None,"style":None,"replica":None})
            await q.edit_message_text("Напишите промт одной строкой — сохраню без изменений.")
            return
        if act == "mem":
            S(uid).update({"mode":"mem","scene":None,"style":None,"replica":None})
            await q.edit_message_text("🎲 Кручу мемный режим…")
            await mem_generate(update, context); return

    if kind == "helper" and rest and rest[0] == "suggest":
        # Помощник сам предложит сцену
        txt = await gpt(SYSTEM_COMMON, "Предложи свою короткую съёмочную сцену на 8 секунд. Верни Заголовок; Сцена.")
        S(uid)["scene"] = txt
        await q.edit_message_text(txt, reply_markup=kb_after_scene_common())
        return

    if kind == "refine":
        how = rest[0]
        base = S(uid).get("scene") or ""
        tweak = "Усиль абсурд, но сохрани логику." if how == "absurd" else "Сделай проще, короче и понятнее."
        txt = await gpt(SYSTEM_ASSIST_REFINE, base + " " + tweak + " Верни ту же структуру.")
        S(uid)["scene"] = txt
        await q.edit_message_text(txt, reply_markup=kb_after_scene_common())
        return

    if kind == "flow":
        step = rest[0]
        if step == "to_style":
            await q.edit_message_text("Выбери стиль:")
            await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles()); return
        if step == "reset":
            S(uid)["scene"] = None
            await q.edit_message_text("Сцена сброшена. Опишите новую идею или выберите режим заново.")
            return

    if kind == "replica" and rest and rest[0] == "gen":
        await generate_replica(update, context, uid); return

    if kind == "style":
        style = rest[0]
        await on_choose_style(q, uid, style); return

    if kind == "go" and rest and rest[0] == "gen":
        await go_generate(update, context, uid); return

    # NEUROKUDO
    if kind == "nk":
        # nk|menu | nk|choose|sub | nk|refine|how | nk|replica|change | nk|again|same | nk|report|...
        act = rest[0]
        if act == "menu":
            S(uid).update({"mode":"nk","nk_mode":None,"scene":None,"style":None,"replica":None})
            await q.edit_message_text("🧪 Режим Как у NEUROKUDO. Выбери подрежим:", reply_markup=kb_nk_mode()); return
        if act == "choose":
            sub = rest[1] if len(rest)>1 else "simple"
            await q.edit_message_text("Генерирую…")
            if sub == "report":
                await nk_report_generate(update, context, uid)
            else:
                await nk_generate(update, context, uid, sub)
            return
        if act == "refine":
            how = rest[1] if len(rest)>1 else "simple"
            await nk_refine(update, context, uid, how); return
        if act == "replica" and len(rest)>1 and rest[1] == "change":
            await nk_change_replica(update, context, uid); return
        if act == "again":
            await nk_again(update, context, uid); return

        # Подпоток репортажа
        if act == "report":
            subact = rest[1] if len(rest)>1 else ""
            if subact == "edit":
                part = rest[2] if len(rest)>2 else "lead"
                await nk_report_edit_ask(update, uid, part); return
            if subact == "replica":
                await nk_report_change_replica(update, context, uid); return
            if subact == "refine":
                how = rest[2] if len(rest)>2 else "simple"
                await nk_report_refine(update, context, uid, how); return

# -----------------------------------------------------------------------------
# Инициализация
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
    log.info(f"LLM_PROVIDER={LLM_PROVIDER}, MODEL={OPENAI_MODEL}")
    app = build_app()
    log.info("Bot is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

