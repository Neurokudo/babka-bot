# main.py – финальный
# Включает:
#  - доступ только для владельца (ID 5015100177)
#  - нижнюю Reply-клавиатуру с кнопкой «🆘 Возникли проблемы»
#  - отправку репортов на почту antonkudo.ai@gmail.com через SMTP
#  - весь функционал: помощник, NEUROKUDO (одна сцена/репортаж из 2 сцен),
#    мемный режим, стили, ориентация (9:16/16:9), богатый JSON-промт,
#    ручное редактирование JSON, показ JSON, пост-кнопки, континуити
#
# .env значения для почты:
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your_gmail@gmail.com
# SMTP_PASS=app_password   # пароль приложения Google
# FROM_EMAIL=your_gmail@gmail.com
# BOT_TOKEN=xxxxxxxxxxxxxx
# OPENAI_API_KEY=sk-...

import os
import json
import random
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

# ========= БАЗА / ОКРУЖЕНИЕ =========
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SMTP для отправки репортов
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER
SUPPORT_TO_EMAIL = "antonkudo.ai@gmail.com"

# (опционально) дублирование репортов в TG-чат(ы): ADMIN_CHAT_ID=-100111,-100222
ADMIN_CHAT_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_IDS = []
if ADMIN_CHAT_RAW:
    for piece in ADMIN_CHAT_RAW.split(","):
        piece = piece.strip()
        if piece:
            try:
                ADMIN_CHAT_IDS.append(int(piece))
            except:
                pass

# ДОСТУП ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА (до релиза)
ALLOWED_USERS = [5015100177]

OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
if "gemini" in (OPENAI_MODEL or "").lower():
    OPENAI_MODEL = "gpt-4o-mini"

DEFAULT_STYLE = "Кино"
DEFAULT_ORIENTATION = "9:16"  # по умолчанию вертикальное

# ========= OPENAI (GPT) =========
from openai import OpenAI
gpt: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        gpt = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI GPT активирован. Модель: %s", OPENAI_MODEL)
    except Exception as e:
        log.error("OpenAI init error: %s", e)

def _sanitize(text: str) -> str:
    if not text:
        return text
    # Удаляем длинные тире и кавычки
    for ch in ['—', '–', '«', '»', '"', "'", '“', '”', '„', '‟']:
        text = text.replace(ch, '')
    text = text.replace('-', '').replace('_', ' ')
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _gpt(system: str, user: str, temperature=0.65, max_tokens=220) -> Optional[str]:
    if not gpt:
        return None
    try:
        r = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature, max_tokens=max_tokens,
        )
        return _sanitize((r.choices[0].message.content or "").strip())
    except Exception as e:
        log.error("GPT error: %s", e)
        return None

# ========= EMAIL / ADMIN NOTIFY =========
def _send_support_email(subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and FROM_EMAIL):
        log.warning("SMTP not configured; skipping email send")
        return False
    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = SUPPORT_TO_EMAIL

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM_EMAIL, [SUPPORT_TO_EMAIL], msg.as_string())
        return True
    except Exception as e:
        log.error("SMTP send failed: %s", e)
        return False

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str):
    for cid in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(chat_id=cid, text=text)
        except Exception as e:
            logging.error("Failed to send report to %s: %s", cid, e)

# ========= ПРЕСЕТЫ СТИЛЕЙ (вливаются в JSON) =========
STYLE_HINTS: Dict[str, Dict[str, str]] = {
    "Pixar": {
        "lighting": "soft global illumination, bright saturated palette, gentle bloom/halation",
        "mood": "whimsical, friendly, optimistic",
        "camera": "clean digital, shallow depth of field, smooth tripod or slow dolly"
    },
    "Киберпанк": {
        "lighting": "neon accents, high contrast, rainy wet surfaces, rim lights",
        "mood": "edgy, urban, tense",
        "camera": "handheld, slight micro-shake, gritty grain"
    },
    "Кино": {
        "lighting": "cinematic key+fill, soft bounce, natural shadows",
        "mood": "grounded, storytelling",
        "camera": "slow dolly or static tripod, anamorphic-like bokeh"
    },
    "Документальный": {
        "lighting": "available light, practical lamps, neutral color",
        "mood": "realistic, grounded",
        "camera": "handheld, slight sway"
    },
    "Арт/Ретро/ЧБ": {
        "lighting": "monochrome/retro film stock feel, pronounced grain, contrast roll-off",
        "mood": "contemplative, nostalgic",
        "camera": "static compositions"
    },
    "ASMR": {
        "lighting": "soft low-contrast light, tactile textures",
        "mood": "calm, intimate",
        "camera": "close perspective, very stable"
    },
    "Бренд": {
        "lighting": "clean studio, softboxes, crisp edges",
        "mood": "premium, minimal",
        "camera": "product-first framing, gentle reveal"
    },
}

def _style_block(style: Optional[str]) -> Dict[str, str]:
    if not style:
        return {}
    return STYLE_HINTS.get(style, {})

# ========= СЦЕНАРНЫЕ ХЕЛПЕРЫ =========
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "complex": "Добавь деталей, сделай сцену насыщеннее и визуально сложнее.",
        "simple": "Упрости сцену, оставь только главное.",
        "absurd": "Сделай сцену более абсурдной и смешной."
    }.get(mode, "Сделай рабочую сцену.")
    sys = (
        "Ты редактор коротких видеосцен. Формулируй именно СЦЕНУ: кто где что делает. "
        "Длительность ~8 секунд, максимум две смены плана. Без поэзии и оценок. "
        "Субтитры и текст в кадре запрещены. Не используй кавычки и тире."
        f" {style} Напиши 1–2 коротких предложения."
    )
    temp = {"normal": 0.65, "complex": 0.85, "simple": 0.55, "absurd": 0.9}[mode]
    return _gpt(sys, user_text, temperature=temp, max_tokens=140) or _sanitize(user_text)

def suggest_replica(scene: str) -> Optional[str]:
    sys = ("Придумай короткую реплику героя к сцене, 4–10 слов. Только сама фраза. "
           "Запрещены кавычки/тире/двоеточия/точка с запятой.")
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ========= NEUROKUDO =========
def generate_nkudo_single_scene() -> str:
    sys = (
        "NEUROKUDO: российский быт + необычный, но РЕАЛЬНЫЙ объект. "
        "Без фантастики. Сцена 8 сек, бытовое действие. 1–2 предложения. "
        "Никаких кавычек и тире."
    )
    return _gpt(sys, "Сгенерируй сцену", temperature=0.75, max_tokens=100) or \
           "Бабушка расчесывает ламу на кухне пятиэтажки"

def generate_nkudo_reportage_scene1() -> str:
    sys = (
        "Репортаж. Сцена 1 (8 сек): русскоязычная журналистка (женщина, 25–40) в деревенском дворе, "
        "говорит короткую фразу в КАМЕРУ по-русски. На заднем плане бабушка с необычным, "
        "но РЕАЛЬНЫМ животным/предметом. Без фантастики. 1–2 предложения. Без кавычек и тире."
    )
    return _gpt(sys, "Создай сцену 1", temperature=0.7, max_tokens=100) or \
           "Журналистка в деревенском дворе говорит в камеру. На фоне бабушка расчёсывает енота"

def generate_nkudo_reportage_scene2(context_scene1: str) -> tuple[str, str]:
    sys = (
        "Репортаж. Сцена 2 (8 сек): крупный план ТОЙ ЖЕ бабушки. Она отвечает по-русски и в конце "
        "говорит короткую финальную фразу-бомбу (3–6 слов). "
        "ВИЗУАЛЬНАЯ КОНТИНУИТИ: те же люди, одежда, двор, предметы/животное — повторить."
    )
    s2 = _gpt(sys, f"Контекст (сцена 1): {context_scene1}", temperature=0.75, max_tokens=120) or \
         "Бабушка в том же дворе, рядом енот; отвечает уверенно и говорит: Вот и весь сказ"
    short = "Вот и весь сказ"
    return s2, short

def generate_nkudo_reportage() -> tuple[str, str, str]:
    s1 = generate_nkudo_reportage_scene1()
    s2, rep = generate_nkudo_reportage_scene2(s1)
    return s1, s2, rep

# ========= VEO CLIENT =========
from veo_client import generate_video_sync

# ========= БОГАТЫЙ JSON-КОНВЕРТЕР =========
def _rich_json_template(scene: str, style: Optional[str], replica: Optional[str],
                        mode: Optional[str], aspect_ratio: str, context: Optional[str]) -> str:
    style_bl = _style_block(style)
    style_text = (
        f'lighting_hint: "{style_bl.get("lighting", "")}", '
        f'mood_hint: "{style_bl.get("mood", "")}", '
        f'camera_hint: "{style_bl.get("camera", "")}"'
    )

    rep_rules = ""
    if mode == "reportage":
        rep_rules = (
            "Reporter must be Russian-speaking female, speak Russian. "
            "No English lines. "
            "Scene 1: reporter speaks to camera; grandmother and object/animal visible behind. "
            "Scene 2: CLOSE on the SAME grandmother in the SAME yard/clothes/object — ensure strict visual continuity. "
            "If context is provided, repeat characters/props/background from it."
        )

    base_rules = (
        "Return VALID JSON only (no comments). "
        "Prohibit any on-screen text/subtitles/logos/watermarks. "
        "Duration strictly 8 seconds."
    )

    sys = (
        "You are a prompt engineer for Google Veo 3.0. "
        f"{base_rules} {rep_rules} "
        "Use this schema (keys in English; values can be Russian where natural):\n"
        "{\n"
        '  "model": "veo-3.0-fast",\n'
        '  "duration": 8,\n'
        '  "aspect_ratio": "9:16|16:9",\n'
        '  "shot": {"composition": "...", "camera_motion": "...", "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},\n'
        '  "subject": {"description": "...", "voice_sync": false},\n'
        '  "scene": {"location": "...", "time_of_day": "..."},\n'
        '  "action": "what happens in 8s concisely",\n'
        '  "voiceover": {"voice": "...", "line": "..."},\n'
        '  "characters": [{"name":"...", "position":"...", "appearance":"...", "action":"..."}],\n'
        '  "ambient": "fx list",\n'
        '  "lighting": "derived from style + scene",\n'
        '  "mood": "derived from style",\n'
        '  "restrictions": "No text or logos."\n'
        "}\n"
        "Respect style hints if given."
    )

    usr = (
        f"scene_text: {scene}\n"
        f"style: {style or 'Без стиля'} ({style_text})\n"
        f"replica: {replica or ''}\n"
        f"aspect_ratio: {aspect_ratio}\n"
    )
    if context:
        usr += f"context_for_continuity: {context}\n"

    if mode == "reportage" and not context:
        usr += (
            "\nGUIDE: опиши так — Репортерша стоит в деревенском дворе, "
            "на заднем плане бабушка с [объект/животное]; репортерша говорит короткую фразу по-русски."
        )

    try:
        r = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": usr}],
            temperature=0.55,
            max_tokens=1300,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        log.error("GPT JSON convert error: %s", e)
        return json.dumps({
            "model": "veo-3.0-fast",
            "duration": 8,
            "aspect_ratio": aspect_ratio,
            "shot": {"composition": "medium shot", "camera_motion": "static", "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},
            "subject": {"description": _sanitize(scene), "voice_sync": False},
            "scene": {"location": "rural yard", "time_of_day": "day"},
            "action": "simple 8 second action",
            "voiceover": {"voice": "female", "line": _sanitize(replica or "")},
            "characters": [],
            "ambient": "light wind, birds",
            "lighting": style_bl.get("lighting", "natural daylight"),
            "mood": style_bl.get("mood", "grounded"),
            "restrictions": "No text or logos"
        }, ensure_ascii=False)

def to_json_prompt(scene: str, style: Optional[str], replica: Optional[str],
                   mode: Optional[str], aspect_ratio: str, context: Optional[str] = None) -> str:
    try:
        json.loads(scene)
        return scene
    except Exception:
        pass
    if not gpt:
        return scene
    return _rich_json_template(scene, style, replica, mode, aspect_ratio, context)

# ========= СОСТОЯНИЕ =========
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        users[uid] = {
            "mode": None,
            "source_text": None,
            "scene": None,
            "style": None,
            "replica": None,
            "awaiting_scene": False,
            "awaiting_custom_style": False,
            "awaiting_scene_edit": False,
            "awaiting_support": False,
            "awaiting_json_edit": False,
            "editing_json_index": 0,   # 0=single, 1=rep scene1, 2=rep scene2
            "editing_scene": None,
            "scene_backup": None,
            "orientation": DEFAULT_ORIENTATION,
            "nkudo_type": None,
            "nkudo_scene1": None,
            "nkudo_scene2": None,
            "last_json": None,
            "last_json1": None,
            "last_json2": None,
        }

# ========= КЛАВИАТУРЫ =========
def reply_main_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🆘 Возникли проблемы")]],
        resize_keyboard=True, one_time_keyboard=False
    )

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео с помощником", callback_data="menu_make")],
        [InlineKeyboardButton("🖼️ Оживление изображения", callback_data="menu_alive")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
        [InlineKeyboardButton("👤 Профиль / Баланс", callback_data="menu_profile")],
        [InlineKeyboardButton("🆘 Возникли проблемы", callback_data="menu_support")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="mode_helper")],
        [InlineKeyboardButton("🔮 Как у NEUROKUDO", callback_data="mode_nkudo")],
        [InlineKeyboardButton("✏️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_back_only():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")]])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Усложни", callback_data="var_complex"),
         InlineKeyboardButton("✂️ Упрости", callback_data="var_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_nkudo_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 Создать как у Neurokudo", callback_data="nkudo_single")],
        [InlineKeyboardButton("🎤 Репортаж из деревни", callback_data="nkudo_reportage")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="back_modes")],
    ])

def kb_nkudo_single():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая сцена", callback_data="nkudo_regenerate_single")],
        [InlineKeyboardButton("🧠✨ Улучшить помощником", callback_data="nkudo_improve_single")],
        [InlineKeyboardButton("➡️ Далее к стилям", callback_data="go_next")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="nkudo_menu_back")],
    ])

def kb_nkudo_reportage_edit():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить сцену 1", callback_data="nkudo_reroll_scene1")],
        [InlineKeyboardButton("🎲 Крутить сцену 2", callback_data="nkudo_reroll_scene2")],
        [InlineKeyboardButton("✏️ Изменить сцену 1", callback_data="nkudo_edit_scene1")],
        [InlineKeyboardButton("✏️ Изменить сцену 2", callback_data="nkudo_edit_scene2")],
        [InlineKeyboardButton("💬 Другая реплика", callback_data="nkudo_new_replica")],
        [InlineKeyboardButton("🔄 Всё заново", callback_data="nkudo_regenerate_report")],
        [InlineKeyboardButton("🧠✨ Улучшить помощником", callback_data="nkudo_improve_report")],
        [InlineKeyboardButton("➡️ Далее к генерации", callback_data="nkudo_approve")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="nkudo_menu_back")],
    ])

def kb_scene_edit():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сохранить", callback_data="scene_save")],
        [InlineKeyboardButton("❌ Отмена", callback_data="scene_cancel")],
    ])

def kb_improve_confirm():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Оставить улучшенное", callback_data="improve_keep")],
        [InlineKeyboardButton("↩️ Отмена (вернуть прежнее)", callback_data="improve_cancel")],
        [InlineKeyboardButton("🔄 Улучшить ещё раз", callback_data="improve_again")],
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
        [InlineKeyboardButton("⏩ Без стиля – далее", callback_data="style_None")],
    ])

def kb_after_style():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="add_replica")],
        [InlineKeyboardButton("👁 Показать JSON", callback_data="show_json")],
        [InlineKeyboardButton("🚀 Создать видео", callback_data="show_final")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_after_replica():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая реплика", callback_data="new_replica")],
        [InlineKeyboardButton("👁 Показать JSON", callback_data="show_json")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="choose_style")],
        [InlineKeyboardButton("🚀 Создать видео", callback_data="show_final")]
    ])

def kb_final_prompt():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Показать JSON", callback_data="show_json")],
        [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")],
        [InlineKeyboardButton("🔄 Переделать", callback_data="go_next")],
    ])

def kb_orientation():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Вертикальное (9:16)", callback_data="ori_916")],
        [InlineKeyboardButton("🖥 Горизонтальное (16:9)", callback_data="ori_169")],
    ])

def kb_meme():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить ещё", callback_data="meme_again")],
        [InlineKeyboardButton("🧠✨ Улучшить с помощником", callback_data="meme_to_helper")],
        [InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_after_video():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить промт", callback_data="edit_from_last")],
        [InlineKeyboardButton("🔁 Сгенерировать ещё", callback_data="menu_make")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back_home")],
    ])

def kb_edit_json(which: str):
    rows = []
    if which == "single":
        rows.append([InlineKeyboardButton("✏️ Изменить JSON", callback_data="edit_json_single")])
    elif which == "rep1":
        rows.append([InlineKeyboardButton("✏️ Изменить JSON сцены 1", callback_data="edit_json1")])
    elif which == "rep2":
        rows.append([InlineKeyboardButton("✏️ Изменить JSON сцены 2", callback_data="edit_json2")])
    rows.append([InlineKeyboardButton("✅ Использовать как есть", callback_data="show_final")])
    return InlineKeyboardMarkup(rows)

# ========= МЕМНЫЙ РЕЖИМ =========
def random_meme_scene() -> str:
    subjects = ["Бабка", "Дед", "Тётка с авоськой", "Дворник", "Курьер", "Официант",
                "Школьник с рюкзаком", "Рокер", "Бизнес леди", "Мужик в телогрейке"]
    locations = ["у подъезда", "на рынке", "в метро", "на остановке", "в парке",
                 "во дворе панельного дома", "на набережной", "у киоска с шаурмой"]
    props = ["арбузом", "самоваром", "гигантским пакетом чипсов", "надувным крокодилом",
             "плюшевым медведем", "огромной лампой торшером", "портретом кота", "резиновым утёнком"]
    items_plural = ["апельсинами", "булочками", "плюшевыми утками", "сосисками в тесте",
                    "листовками", "ладошками из поролона", "магнитиками", "стеклянными банками"]
    npcs = ["охранником", "продавщицей семечек", "контролёром", "диспетчером такси", "дворовой кошкой"]
    vehicles = ["скейтборде", "самокате", "тележке из супермаркета", "велике без седла"]
    templates = [
        "{s} едет на {veh} {loc}",
        "{s} спорит с {npc} {loc}",
        "{s} жонглирует {items} {loc}",
        "{s} танцует с {prop} {loc}",
        "{s} раздаёт {items} {loc}",
        "{s} пытается упаковать {prop} в пакет {loc}",
        "{s} толкает тележку с {prop} {loc}",
        "{s} фотографируется с {prop} {loc}",
    ]
    t = random.choice(templates); s = random.choice(subjects); loc = random.choice(locations)
    if "{veh}" in t:  return _sanitize(t.format(s=s, veh=random.choice(vehicles), loc=loc))
    if "{npc}" in t:  return _sanitize(t.format(s=s, npc=random.choice(npcs), loc=loc))
    if "{items}" in t:return _sanitize(t.format(s=s, items=random.choice(items_plural), loc=loc))
    return _sanitize(t.format(s=s, prop=random.choice(props), loc=loc))

# ========= ДОСТУП =========
async def check_access(update: Update) -> bool:
    uid = update.effective_user.id
    if uid not in ALLOWED_USERS:
        try:
            if update.message:
                await update.message.reply_text("🚧 Бот пока закрыт для теста. Доступ только у владельца.")
            elif update.callback_query:
                await update.callback_query.message.reply_text("🚧 Бот пока закрыт для теста. Доступ только у владельца.")
        except:
            pass
        return False
    return True

# ========= ХЭНДЛЕРЫ =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    users[uid].update({
        "mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
        "awaiting_scene": False, "awaiting_custom_style": False, "awaiting_scene_edit": False,
        "awaiting_support": False, "awaiting_json_edit": False, "editing_json_index": 0
    })
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_home())
    # Включаем нижнюю клавиатуру
    await update.message.reply_text("Нижняя кнопка для связи включена.", reply_markup=reply_main_kb())

async def cmd_whereami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    chat = update.effective_chat
    await update.message.reply_text(
        f"chat_id: {chat.id}\n"
        f"type: {chat.type}\n"
        f"title: {getattr(chat, 'title', '')}"
    )

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    # Нижняя кнопка «Возникли проблемы»
    if text == "🆘 Возникли проблемы":
        st["awaiting_support"] = True
        await update.message.reply_text("Опиши проблему одним сообщением — я перешлю её разработчику на почту.")
        return

    # Приём репорта
    if st.get("awaiting_support"):
        st["awaiting_support"] = False
        body = f"Репорт от @{update.effective_user.username or uid} (ID {uid}):\n\n{text}"
        ok = _send_support_email("🆘 Репорт из Babka Bot", body)
        if ADMIN_CHAT_IDS:
            await notify_admins(context, f"🆘 Репорт от {uid}:\n\n{text}")
        if ok:
            await update.message.reply_text("✅ Репорт отправлен на почту разработчика.", reply_markup=reply_main_kb())
        else:
            await update.message.reply_text("⚠️ Не удалось отправить на почту. Проверь SMTP-настройки.", reply_markup=reply_main_kb())
        return

    # Репортаж – редактирование текста сцены
    if st.get("awaiting_scene_edit"):
        editing = st.get("editing_scene")
        if editing == 1: st["nkudo_scene1"] = text; await update.message.reply_text("✅ Сцена 1 обновлена!")
        elif editing == 2: st["nkudo_scene2"] = text; await update.message.reply_text("✅ Сцена 2 обновлена!")
        st["awaiting_scene_edit"] = False
        result_text = ("📮 Текущий репортаж:\n\n"
                       f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
                       f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
                       f"💬 Реплика: {st.get('replica','')}")
        await update.message.reply_text(result_text, reply_markup=kb_nkudo_reportage_edit()); return

    # Кастом стиль
    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"✅ Выбран стиль: {st['style']}")
        await update.message.reply_text("Что делаем дальше?", reply_markup=kb_after_style()); return

    # Ожидание сцены (manual/helper)
    if st["awaiting_scene"]:
        st["awaiting_scene"] = False; st["source_text"] = text
        if st["mode"] == "helper" and gpt:
            scene = improve_scene(text, mode="normal"); st["scene"] = scene
            await update.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{scene}", reply_markup=kb_variants()); return
        st["scene"] = text
        await update.message.reply_text(f"📝 Промт принят:\n\n{text}", reply_markup=kb_variants()); return

    # По умолчанию
    await update.message.reply_text("Главное меню:", reply_markup=kb_home())
    await update.message.reply_text("Готов к новым задачам.", reply_markup=reply_main_kb())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; _ensure(uid); st = users[uid]; data = q.data
    log.info("Button: %s", data)

    # Главные пункты
    if data == "menu_make":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await q.message.edit_text("🖼️ Оживление изображения (в разработке)."); return
    if data == "menu_guides":
        await q.message.edit_text("📚 Гайды и оплата – скоро тут ❤️"); return
    if data == "menu_profile":
        await q.message.edit_text("👤 Профиль/Баланс – скоро доступно."); return
    if data == "menu_support":
        st["awaiting_support"] = True
        await q.message.edit_text("🆘 Опишите проблему одним сообщением — отправлю на почту. Чтобы отменить: /start"); return
    if data == "back_home":
        await q.message.edit_text("Главное меню:", reply_markup=kb_home())
        try:
            await q.message.reply_text("Готов к новым задачам.", reply_markup=reply_main_kb())
        except:
            pass
        return

    # Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("🧠✨ Режим умного помощника активирован!")
        await q.message.reply_text("Опиши сцену — сделаю её съёмочной на ~8 секунд.", reply_markup=kb_back_only()); return

    if data == "mode_manual":
        st.update({"mode": "manual", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("✏️ Режим ручного ввода активирован!")
        await q.message.reply_text("Введи свою сцену (я ничего не меняю).", reply_markup=kb_back_only()); return

    if data == "mode_meme":
        st.update({"mode": "meme", "style": None, "replica": None})
        scene = random_meme_scene(); st["scene"] = scene
        await q.message.edit_text("🎲 Мемный режим активирован!")
        await q.message.reply_text(f"🎭 Случайная сцена:\n\n{scene}", reply_markup=kb_meme()); return

    if data == "meme_again":
        scene = random_meme_scene(); st["scene"] = scene
        await q.message.edit_text(f"🎭 Новая сцена:\n\n{scene}", reply_markup=kb_meme()); return

    if data == "meme_to_helper":
        st["mode"] = "helper"; st["source_text"] = st.get("scene"); st["scene"] = improve_scene(st["scene"], "normal")
        await q.message.edit_text(f"🧠✨ Улучшено помощником:\n\n{st['scene']}", reply_markup=kb_variants()); return

    if data == "mode_nkudo":
        st.update({"mode": "nkudo", "scene": None, "style": None, "replica": None})
        await q.message.edit_text("🔮 Режим «Как у NEUROKUDO» активирован!")
        explanation = ("🔮 Экспериментальный режим создания сцен и репортажей.\n\nВыберите тип сюжета:")
        await q.message.reply_text(explanation, reply_markup=kb_nkudo_menu()); return
    if data == "back_modes":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "nkudo_menu_back":
        await q.message.edit_text("Выберите тип сюжета:", reply_markup=kb_nkudo_menu()); return

    # NEUROKUDO — одиночная
    if data == "nkudo_single":
        await q.message.edit_text("⏳ Генерирую сцену...")
        st["scene"] = generate_nkudo_single_scene(); st["nkudo_type"] = "single"
        txt = "🔮 Сгенерирована сцена в стиле NEUROKUDO\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_single()); return
    if data == "nkudo_regenerate_single":
        await q.message.edit_text("🔄 Генерирую новую сцену...")
        st["scene"] = generate_nkudo_single_scene()
        txt = "🔮 Новая сцена сгенерирована\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_single()); return
    if data == "nkudo_improve_single":
        if st.get("scene"):
            st["scene_backup"] = st["scene"]; st["scene"] = improve_scene(st["scene"], mode="complex")
            txt = "🧠✨ Сцена улучшена помощником\n\n🎬 Улучшенная сцена:\n" + st["scene"] + "\n\nОставить улучшенную версию?"
            await q.message.edit_text(txt, reply_markup=kb_improve_confirm()); return

    # NEUROKUDO — репортаж
    if data == "nkudo_reportage":
        await q.message.edit_text("⏳ Генерирую репортаж из деревни...")
        s1 = generate_nkudo_reportage_scene1()
        s2, rep = generate_nkudo_reportage_scene2(s1)
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2; st["replica"] = rep
        st["scene"] = f"{s1}\n\n{s2}"; st["nkudo_type"] = "reportage"
        txt = ("🔮 Сгенерирован репортаж\n\n"
               f"📺 Сцена 1: {s1}\n\n"
               f"🎤 Сцена 2: {s2}\n\n"
               f"💬 Реплика: {rep}\n\n"
               "Общая длительность ~16 сек")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_reroll_scene1":
        st["nkudo_scene1"] = generate_nkudo_reportage_scene1()
        await q.message.edit_text(f"🔄 Новая сцена 1:\n\n{st['nkudo_scene1']}", reply_markup=kb_nkudo_reportage_edit()); return
    if data == "nkudo_reroll_scene2":
        s2, rep = generate_nkudo_reportage_scene2(st.get("nkudo_scene1",""))
        st["nkudo_scene2"] = s2; st["replica"] = rep
        await q.message.edit_text(f"🔄 Новая сцена 2:\n\n{st['nkudo_scene2']}\n\n💬 Реплика: {rep}",
                                  reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_edit_scene1":
        st["editing_scene"] = 1; st["awaiting_scene_edit"] = True
        await q.message.reply_text(f"✏️ Редактирование сцены 1:\n\n{st.get('nkudo_scene1','')}\n\nОтправьте новый текст:",
                                   reply_markup=kb_scene_edit()); return
    if data == "nkudo_edit_scene2":
        st["editing_scene"] = 2; st["awaiting_scene_edit"] = True
        await q.message.reply_text(f"✏️ Редактирование сцены 2:\n\n{st.get('nkudo_scene2','')}\n\nОтправьте новый текст:",
                                   reply_markup=kb_scene_edit()); return
    if data == "scene_save":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("✅ Изменения сохранены!")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Реплика: {st.get('replica','')}")
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return
    if data == "scene_cancel":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("❌ Редактирование отменено")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Реплика: {st.get('replica','')}")
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_new_replica":
        sys = ("Короткая финальная фраза бабушки (3–6 слов, по-русски). Без кавычек/тире/двоеточий.")
        st["replica"] = _gpt(sys, f"Контекст: {st.get('nkudo_scene2','')}", temperature=0.8, max_tokens=25) or "Поехали уже"
        await q.message.edit_text(f"💬 Новая реплика: {st['replica']}", reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_regenerate_report":
        await q.message.edit_text("🔄 Генерирую новый репортаж...")
        s1 = generate_nkudo_reportage_scene1()
        s2, rep = generate_nkudo_reportage_scene2(s1)
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2; st["replica"] = rep
        st["scene"] = f"{s1}\n\n{s2}"
        txt = f"🔮 Новый репортаж\n\n📺 Сцена 1: {s1}\n\n🎤 Сцена 2: {s2}\n\n💬 Реплика: {rep}"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_improve_report":
        if st.get("nkudo_scene1") and st.get("nkudo_scene2"):
            st["scene1_backup"] = st["nkudo_scene1"]; st["scene2_backup"] = st["nkudo_scene2"]
            st["nkudo_scene1"] = improve_scene(st["nkudo_scene1"], "complex")
            st["nkudo_scene2"] = improve_scene(st["nkudo_scene2"], "normal")
            st["scene"] = f"{st['nkudo_scene1']}\n\n{st['nkudo_scene2']}"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оставить улучшенное", callback_data="report_improve_keep")],
                [InlineKeyboardButton("↩️ Отмена (вернуть прежнее)", callback_data="report_improve_cancel")],
            ])
            txt = ("🧠✨ Сцены улучшены.\n\n"
                   f"📺 Сцена 1: {st['nkudo_scene1']}\n\n"
                   f"🎤 Сцена 2: {st['nkudo_scene2']}\n\n"
                   f"💬 Реплика: {st.get('replica','')}")
            await q.message.edit_text(txt, reply_markup=kb); return
    if data == "report_improve_keep":
        st["scene1_backup"] = None; st["scene2_backup"] = None
        await q.message.edit_text("✅ Улучшенная версия сохранена!")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Реплика: {st.get('replica','')}")
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return
    if data == "report_improve_cancel":
        if st.get("scene1_backup") and st.get("scene2_backup"):
            st["nkudo_scene1"] = st["scene1_backup"]; st["nkudo_scene2"] = st["scene2_backup"]
            st["scene"] = f"{st['nkudo_scene1']}\n\n{st['nkudo_scene2']}"
            st["scene1_backup"] = None; st["scene2_backup"] = None
            await q.message.edit_text("↩️ Возвращена прежняя версия!")
            txt = ("📮 Текущий репортаж:\n\n"
                   f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
                   f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
                   f"💬 Реплика: {st.get('replica','')}")
            await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_approve":
        if st.get("nkudo_type") == "reportage":
            st["style"] = "Документальный"
            await q.message.edit_text(
                "✅ Сюжет утвержден!\n\n"
                "📺 Общая длительность: 16 секунд (2 сцены по 8 сек)\n"
                "🎨 Стиль: Документальный репортаж\n\n"
                "Готово к генерации видео!"
            )
            await q.message.reply_text("📝 Итоговый промпт:\n\n"
                                       f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
                                       f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
                                       f"💬 Реплика: {st.get('replica','')}")
            await q.message.reply_text("Выбери ориентацию:", reply_markup=kb_orientation())
            await q.message.reply_text("Когда готов — запускаем:", reply_markup=kb_final_prompt()); return

    # Варианты улучшения
    if data == "var_complex" and st.get("source_text") and gpt:
        st["scene"] = improve_scene(st["source_text"], "complex")
        await q.message.edit_text(f"🔍 Усложнено:\n\n{st['scene']}", reply_markup=kb_variants()); return
    if data == "var_simple" and st.get("source_text") and gpt:
        st["scene"] = improve_scene(st["source_text"], "simple")
        await q.message.edit_text(f"✂️ Упрощено:\n\n{st['scene']}", reply_markup=kb_variants()); return
    if data == "var_again" and st.get("source_text") and gpt:
        st["scene"] = improve_scene(st["source_text"], "normal")
        await q.message.edit_text(f"🔄 Переделано:\n\n{st['scene']}", reply_markup=kb_variants()); return

    # Переход к стилям
    if data in ("go_next", "choose_style"):
        if st.get("scene"): await q.message.edit_text(f"✅ Сцена готова:\n\n{st['scene']}")
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles()); return

    # Стили
    if data.startswith("style_"):
        val = data.split("_", 1)[1]
        if val == "custom":
            st["awaiting_custom_style"] = True
            await q.message.edit_text("✏️ Напишите желаемый стиль для видео:"); return
        st["style"] = None if val == "None" else val
        await q.message.edit_text(f"✅ Выбран стиль: {st['style'] or 'Без стиля'}")
        await q.message.reply_text("Что делаем дальше?", reply_markup=kb_after_style()); return

    # Реплики
    if data in ("add_replica", "new_replica"):
        if not st.get("scene"): await q.message.reply_text("Сначала опиши сцену."); return
        st["replica"] = suggest_replica(st["scene"]) or "Поехали уже!"
        if data == "new_replica":
            await q.message.edit_text(f"✅ Создана реплика: {st['replica']}", reply_markup=kb_after_replica())
        else:
            await q.message.edit_text(f"✅ Создана реплика: {st['replica']}")
            await q.message.reply_text("Готово! Можно генерировать другую реплику или смотреть промпт.", reply_markup=kb_after_replica())
        return

    # Показ JSON + редактирование
    if data == "show_json":
        if st.get("nkudo_type") == "reportage":
            j1 = to_json_prompt(st.get("nkudo_scene1",""), st.get("style"), None, "reportage",
                                aspect_ratio=st.get("orientation", DEFAULT_ORIENTATION), context=None)
            j2 = to_json_prompt(st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage",
                                aspect_ratio=st.get("orientation", DEFAULT_ORIENTATION), context=st.get("nkudo_scene1"))
            st["last_json1"], st["last_json2"] = j1, j2
            await q.message.reply_text("🧾 JSON — Сцена 1:\n```\n" + j1 + "\n```", parse_mode="Markdown",
                                       reply_markup=kb_edit_json("rep1"))
            await q.message.reply_text("🧾 JSON — Сцена 2:\n```\n" + j2 + "\n```", parse_mode="Markdown",
                                       reply_markup=kb_edit_json("rep2"))
        else:
            jj = to_json_prompt(st.get("scene",""), st.get("style"), st.get("replica"), st.get("mode"),
                                aspect_ratio=st.get("orientation", DEFAULT_ORIENTATION), context=None)
            st["last_json"] = jj
            await q.message.reply_text("🧾 JSON-промт:\n```\n" + jj + "\n```", parse_mode="Markdown",
                                       reply_markup=kb_edit_json("single"))
        return

    if data == "edit_json_single":
        st["awaiting_json_edit"] = True; st["editing_json_index"] = 0
        await q.message.reply_text("✏️ Вставьте новый JSON (единственная сцена)."); return
    if data == "edit_json1":
        st["awaiting_json_edit"] = True; st["editing_json_index"] = 1
        await q.message.reply_text("✏️ Вставьте новый JSON для Сцены 1."); return
    if data == "edit_json2":
        st["awaiting_json_edit"] = True; st["editing_json_index"] = 2
        await q.message.reply_text("✏️ Вставьте новый JSON для Сцены 2."); return

    # Финальный промпт + ориентация
    if data == "show_final":
        if not st.get("scene"): await q.message.reply_text("Сначала опиши сцену."); return
        final_text = "📝 Итоговый промпт:\n\n"
        final_text += f"🎬 Сцена: {st['scene']}\n\n"
        if st.get("style"): final_text += f"🎨 Стиль: {st['style']}\n\n"
        if st.get("replica"): final_text += f"💬 Реплика: {st['replica']}\n\n"
        final_text += "Всё готово для генерации!"
        await q.message.reply_text(final_text)
        await q.message.reply_text("Выбери ориентацию:", reply_markup=kb_orientation())
        await q.message.reply_text("Когда готов — запускаем:", reply_markup=kb_final_prompt()); return

    # Ориентация
    if data == "ori_916":
        st["orientation"] = "9:16"; await q.message.edit_text("✅ Ориентация: Вертикальное (9:16)"); return
    if data == "ori_169":
        st["orientation"] = "16:9"; await q.message.edit_text("✅ Ориентация: Горизонтальное (16:9)"); return

    # Генерация
    if data == "generate_now":
        if not st.get("scene"): await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None: st["style"] = DEFAULT_STYLE
        if not st.get("orientation"): st["orientation"] = DEFAULT_ORIENTATION
        try: await q.message.edit_reply_markup(reply_markup=None)
        except: pass

        msg = await q.message.reply_text("⏳ Генерирую видео… Это может занять несколько минут.")
        try:
            # REPORTAGE — два видео
            if st.get("nkudo_type") == "reportage" or st.get("mode") == "reportage":
                prompt1 = st.get("last_json1") or to_json_prompt(
                    st.get("nkudo_scene1",""), st.get("style"), None, "reportage",
                    aspect_ratio=st["orientation"], context=None
                )
                prompt2 = st.get("last_json2") or to_json_prompt(
                    st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage",
                    aspect_ratio=st["orientation"], context=st.get("nkudo_scene1")
                )
                st["last_json1"], st["last_json2"] = prompt1, prompt2

                from veo_client import generate_video_sync
                res1 = await asyncio.to_thread(generate_video_sync, prompt1, duration=8, aspect_ratio=st["orientation"])
                vids1 = (res1 or {}).get("videos", [])
                if vids1 and vids1[0].get("file_path") and os.path.exists(vids1[0]["file_path"]):
                    with open(vids1[0]["file_path"], "rb") as f:
                        await q.message.reply_video(video=f, caption="📺 Сцена 1", supports_streaming=True)
                else:
                    await q.message.reply_text("⚠️ Сцена 1: видео не вернулось.")

                res2 = await asyncio.to_thread(generate_video_sync, prompt2, duration=8, aspect_ratio=st["orientation"])
                vids2 = (res2 or {}).get("videos", [])
                cap2 = "🎤 Сцена 2" + (f"\n💬 {st.get('replica')}" if st.get("replica") else "")
                if vids2 and vids2[0].get("file_path") and os.path.exists(vids2[0]["file_path"]):
                    with open(vids2[0]["file_path"], "rb") as f:
                        await q.message.reply_video(video=f, caption=cap2, supports_streaming=True)
                else:
                    await q.message.reply_text("⚠️ Сцена 2: видео не вернулось.")

                await q.message.reply_text("Готово! Что дальше?", reply_markup=kb_after_video())
                await q.message.reply_text("Быстрый доступ к связи включён.", reply_markup=reply_main_kb())
                return

            # Обычные режимы — одно видео
            prompt = st.get("last_json") or to_json_prompt(
                st["scene"], st.get("style"), st.get("replica"), st.get("mode"),
                aspect_ratio=st["orientation"], context=None
            )
            st["last_json"] = prompt

            from veo_client import generate_video_sync
            res = await asyncio.to_thread(generate_video_sync, prompt, duration=8, aspect_ratio=st["orientation"])
            videos = (res or {}).get("videos", [])
            if not videos:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home())
                await q.message.reply_text("Связь с разработчиком:", reply_markup=reply_main_kb())
                return

            v0 = videos[0]; file_path = v0.get("file_path"); uri = v0.get("uri")
            caption = (f"✅ Видео готово!\n\n🎬 Сцена: {st['scene']}\n🎨 Стиль: {st['style']}" +
                       (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "") +
                       f"\n📐 Ориентация: {st['orientation']}")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await q.message.reply_video(video=f, caption=caption, supports_streaming=True, reply_markup=kb_after_video())
            elif uri:
                await q.message.reply_text(f"{caption}\n\n🔗 GCS: {uri}", reply_markup=kb_after_video())
            else:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home())

            await q.message.reply_text("Если что-то пошло не так — напиши:", reply_markup=reply_main_kb())

        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"⚠️ Ошибка генерации: {e}\n\nПопробуйте ещё раз.", reply_markup=kb_home())
            await q.message.reply_text("Связаться со мной:", reply_markup=reply_main_kb())
        finally:
            try: await msg.delete()
            except: pass
        return

    # Пост-кнопки после видео
    if data == "edit_from_last":
        st["awaiting_scene"] = True
        await q.message.reply_text("✏️ Отправьте новый текст сцены. Текущая версия ниже.")
        await q.message.reply_text(f"Текущая сцена:\n\n{st.get('scene','')}", reply_markup=kb_back_only())
        return

    # fallback
    await q.message.reply_text("Команда пока не поддерживается. Возврат в меню.", reply_markup=kb_home())
    await q.message.reply_text("Связаться со мной:", reply_markup=reply_main_kb())

# ========= ЗАПУСК =========
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whereami", cmd_whereami))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Bot is running…")
    app.run_polling()

if __name__ == "__main__":
    main()

