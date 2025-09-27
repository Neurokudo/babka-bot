# main.py – полный: меню, помощник, NEUROKUDO/репортаж, мемы, стили, ориентация, JSON, саппорт
import os
import json
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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # опционально: куда слать жалобы

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
    text = text.replace('"', '').replace("'", '').replace('-', '').replace('_', ' ')
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _gpt(system: str, user: str, temperature=0.7, max_tokens=220) -> Optional[str]:
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

# ========= ПРЕСЕТЫ СТИЛЕЙ (вливаются в JSON) =========
STYLE_HINTS: Dict[str, str] = {
    "Pixar": ("bright saturated palette, soft global illumination, clean surfaces, "
              "gentle vignetting, subtle filmic halation, shallow depth of field, "
              "expressive but realistic motion; friendly whimsical mood"),
    "Киберпанк": ("neon accents, rainy night, high contrast, wet reflective surfaces, "
                  "holographic signs, low key lighting, handheld micro-shake, grain; edgy mood"),
    "Кино": ("cinematic color grading (teal & orange bias), anamorphic bokeh, "
             "soft key + strong rim light, slow dolly or tripod, naturalistic performances"),
    "Документальный": ("handheld camera, neutral color, available light, practical lamps, "
                       "diegetic ambience, minimal post-processing; grounded realistic mood"),
    "Арт/Ретро/ЧБ": ("monochrome or retro film stock, pronounced grain, contrast roll-off, "
                     "static composition, slow tempo; contemplative mood"),
    "ASMR": ("very quiet ambience, close perspective, soft textures, gentle motions, "
             "intimate space; calming mood"),
    "Бренд": ("clean minimal composition, product-first framing, soft studio light, "
              "crisp edges, gentle camera reveal; premium mood"),
}

# ========= СЦЕНАРНЫЕ ХЕЛПЕРЫ =========
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "complex": "Добавь больше деталей, сделай сцену насыщеннее и сложнее визуально.",
        "simple": "Сделай сцену проще, убери лишние детали, оставь только главное.",
        "absurd": "Сделай сцену более абсурдной и смешной."
    }.get(mode, "Сделай рабочую сцену.")
    sys = (
        "Ты редактор коротких видеосцен. Формулируй именно СЦЕНУ: кто где что делает. "
        "Длительность ~8 секунд, максимум две смены плана. Только действие и визуальные детали, "
        "без поэтики/оценок. Запрещены текст/субтитры в кадре. Не используй кавычки и тире. "
        f"{style} Напиши 1–2 коротких предложения."
    )
    temp = {"normal": 0.65, "complex": 0.85, "simple": 0.55, "absurd": 0.9}[mode]
    return _gpt(sys, user_text, temperature=temp, max_tokens=140) or _sanitize(user_text)

def suggest_replica(scene: str) -> Optional[str]:
    sys = ("Придумай короткую реплику героя к сцене, 4–10 слов. Только сама фраза. "
           "ЗАПРЕЩЕНЫ кавычки, тире, двоеточия, точка с запятой.")
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ========= NEUROKUDO =========
def generate_nkudo_single_scene() -> str:
    sys = (
        "NEUROKUDO: обычный российский быт + необычный, но РЕАЛЬНЫЙ объект (без фантастики). "
        "Сцена 8 сек, бытовое действие. Примеры: бабушка кормит страуса на балконе; "
        "дед выгуливает альпаку; бабушка моет слонёнка; дед учит ара читать газету. "
        "Никаких кавычек и тире. 1–2 предложения."
    )
    return _gpt(sys, "Сгенерируй сцену", temperature=0.75, max_tokens=100) or \
           "Бабушка расчесывает ламу на кухне пятиэтажки"

def generate_nkudo_reportage() -> tuple[str, str, str]:
    sys1 = (
        "Репортаж. Сцена 1 (8 сек): русскоязычная журналистка (женщина, 25–40) в деревне, "
        "говорит короткую фразу в КАМЕРУ по-русски. На заднем плане бабушка с необычным, "
        "но РЕАЛЬНЫМ животным/объектом. Без фантастики. 1–2 предложения. Без кавычек и тире."
    )
    scene1 = _gpt(sys1, "Создай сцену 1", temperature=0.7, max_tokens=100)

    sys2 = (
        "Сцена 2 (8 сек): крупный план той же бабушки. Она отвечает по-русски и в конце говорит "
        "короткую финальную фразу-бомбу (3–6 слов, без кавычек/тире/двоеточий). "
        "ВИЗУАЛЬНАЯ КОНТИНУИТИ: те же персонажи, одежда, двор, предметы, животное — повторить, "
        "чтобы зрительно совпадало со сценой 1."
    )
    scene2 = _gpt(sys2, f"Контекст: {scene1}", temperature=0.75, max_tokens=120)
    replica = "Вот и весь сказ"
    return (scene1 or "", scene2 or "", replica)

# ========= VEO CLIENT =========
from veo_client import generate_video_sync

# ========= СЕКРЕТНЫЙ JSON-КОНВЕРТЕР (+показ JSON) =========
def style_hint(style: Optional[str]) -> str:
    if not style: return ""
    return STYLE_HINTS.get(style, "")

def to_json_prompt(scene: str, style: Optional[str], replica: Optional[str],
                   mode: Optional[str], context: Optional[str] = None) -> str:
    """
    Если scene уже JSON -> возвращаем как есть.
    Иначе: превращаем в структурный JSON для Veo с учётом стиля и (для репортажа) контекста.
    """
    try:
        json.loads(scene)
        return scene
    except Exception:
        pass

    if not gpt:
        return scene

    style_txt = style_hint(style)
    base_rules = (
        "Верни ТОЛЬКО валидный JSON без комментариев.\n"
        "Структура:\n"
        "{\n"
        '  "shot": {"composition": "...", "camera_motion": "...", "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},\n'
        '  "environment": {"location": "...", "time_of_day": "...", "weather": "..."},\n'
        '  "characters": [{"name": "...", "position": "...", "appearance": "...", "action": "..."}],\n'
        '  "dialogue": [{"character": "...", "voice": "...", "line": "..."}],\n'
        '  "lighting": "...", "ambient": "...", "mood": "...", "constraints": "no on-screen text or subtitles"\n'
        "}\n"
        "Не добавляй субтитры/текст в кадре."
    )
    sys = (
        "Ты промт-инженер Veo 3.0. Преврати описание сцены в JSON для видеогенерации. "
        + base_rules
    )
    if mode == "nkudo":
        sys += " Стиль сцены: бытовуха + необычный реальный объект, реализм, лёгкий юмор."
    elif mode == "meme":
        sys += " Сделай гротескно и смешно, но реалистично снимаемо."
    elif mode == "reportage":
        sys += (" Формат: новостной репортаж, русский язык. "
                "Сцена 1: журналистка говорит. Сцена 2: бабушка отвечает. "
                "Для сцены 2 обязательно соблюдай ВИЗУАЛЬНУЮ КОНТИНУИТИ — повтори тех же людей, "
                "одежду, предметы, животное, фон.")
    else:
        sys += " Сделай съёмочную сцену с реалистичными действиями."

    if style_txt:
        sys += f" Впитай требования стиля: {style_txt}"

    usr = f"Сцена: {scene}\nСтиль: {style or ''}\nРеплика: {replica or ''}"
    if context:
        usr += f"\nКонтекст/сцена_1 (для континуити): {context}"

    try:
        r = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": usr}],
            temperature=0.55,
            max_tokens=1200,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        log.error("GPT JSON convert error: %s", e)
        return scene

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

# ========= ХЭНДЛЕРЫ =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; _ensure(uid)
    users[uid].update({
        "mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
        "awaiting_scene": False, "awaiting_custom_style": False, "awaiting_scene_edit": False,
        "awaiting_support": False,
    })
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_home())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    # Support
    if st.get("awaiting_support"):
        st["awaiting_support"] = False
        await update.message.reply_text("✅ Спасибо! Сообщение принято. Мы свяжемся при необходимости.", reply_markup=kb_home())
        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID),
                                               text=f"🆘 Репорт от {uid}:\n\n{text}")
            except Exception as e:
                log.error("Failed to forward support message: %s", e)
        return

    # Репортаж – редактирование
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

    await update.message.reply_text("Главное меню:", reply_markup=kb_home())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; _ensure(uid); st = users[uid]; data = q.data
    log.info("Button: %s", data)

    # Главные пункты
    if data == "menu_make":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await q.message.edit_text("🖼️ Оживление изображения: пришлите фото и короткий промт (в разработке)."); return
    if data == "menu_guides":
        await q.message.edit_text("📚 Гайды и оплата – скоро тут ❤️"); return
    if data == "menu_profile":
        await q.message.edit_text("👤 Профиль/Баланс – скоро доступно."); return
    if data == "menu_support":
        st["awaiting_support"] = True
        await q.message.edit_text("🆘 Опишите проблему текстом — отправлю админу. Чтобы отменить: /start"); return
    if data == "back_home":
        await q.message.edit_text("Главное меню:", reply_markup=kb_home()); return

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

    # NEUROKUDO — одиночная
    if data == "nkudo_menu_back":
        await q.message.edit_text("Выберите тип сюжета:", reply_markup=kb_nkudo_menu()); return
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
        s1, s2, rep = generate_nkudo_reportage()
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2 if "говорит:" in s2 else f"{s2} и говорит: {rep}"
        st["replica"] = rep; st["scene"] = f"{s1}\n\n{st['nkudo_scene2']}"; st["nkudo_type"] = "reportage"
        txt = ("🔮 Сгенерирован репортаж\n\n"
               f"📺 Сцена 1: {s1}\n\n🎤 Сцена 2: {st['nkudo_scene2']}\n\nОбщая длительность ~16 сек")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_edit_scene1":
        st["editing_scene"] = 1; st["awaiting_scene_edit"] = True
        await q.message.reply_text(f"✏️ Редактирование сцены 1:\n\n{st.get('nkudo_scene1','')}\n\nОтправьте новый текст:", reply_markup=kb_scene_edit()); return
    if data == "nkudo_edit_scene2":
        st["editing_scene"] = 2; st["awaiting_scene_edit"] = True
        await q.message.reply_text(f"✏️ Редактирование сцены 2:\n\n{st.get('nkudo_scene2','')}\n\nОтправьте новый текст:", reply_markup=kb_scene_edit()); return
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
        sys = ("Короткая финальная фраза бабушки для репортажа (3–6 слов, по-русски). Без кавычек/тире/двоеточий.")
        st["replica"] = _gpt(sys, f"Контекст: {st.get('nkudo_scene2','')}", temperature=0.8, max_tokens=25) or "Поехали уже"
        base2 = st.get("nkudo_scene2","")
        if " говорит:" in base2: base2 = base2.split(" говорит:")[0]
        st["nkudo_scene2"] = f"{base2} говорит: {st['replica']}"
        st["scene"] = f"{st.get('nkudo_scene1','')}\n\n{st['nkudo_scene2']}"
        txt = f"💬 Новая реплика: {st['replica']}\n\n🎤 Сцена 2: {st['nkudo_scene2']}"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_regenerate_report":
        await q.message.edit_text("🔄 Генерирую новый репортаж...")
        s1, s2, rep = generate_nkudo_reportage()
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2 if "говорит:" in s2 else f"{s2} говорит: {rep}"
        st["replica"] = rep; st["scene"] = f"{s1}\n\n{st['nkudo_scene2']}"
        txt = f"🔮 Новый репортаж\n\n📺 Сцена 1: {s1}\n\n🎤 Сцена 2: {st['nkudo_scene2']}"
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

    # Показ JSON
    if data == "show_json":
        if st.get("nkudo_type") == "reportage":
            j1 = to_json_prompt(st.get("nkudo_scene1",""), st.get("style"), None, "reportage")
            j2 = to_json_prompt(st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage",
                                context=st.get("nkudo_scene1"))
            st["last_json1"], st["last_json2"] = j1, j2
            await q.message.reply_text("🧾 JSON — Сцена 1:\n```\n" + j1 + "\n```", parse_mode="Markdown")
            await q.message.reply_text("🧾 JSON — Сцена 2:\n```\n" + j2 + "\n```", parse_mode="Markdown")
        else:
            jj = to_json_prompt(st.get("scene",""), st.get("style"), st.get("replica"), st.get("mode"))
            st["last_json"] = jj
            await q.message.reply_text("🧾 JSON-промт:\n```\n" + jj + "\n```", parse_mode="Markdown")
        return

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
                prompt1 = to_json_prompt(st.get("nkudo_scene1",""), st.get("style"), None, "reportage")
                prompt2 = to_json_prompt(st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage",
                                         context=st.get("nkudo_scene1"))
                st["last_json1"], st["last_json2"] = prompt1, prompt2

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
                return

            # Обычные режимы — одно видео
            prompt = to_json_prompt(st["scene"], st.get("style"), st.get("replica"), st.get("mode"))
            st["last_json"] = prompt
            res = await asyncio.to_thread(generate_video_sync, prompt, duration=8, aspect_ratio=st["orientation"])
            videos = (res or {}).get("videos", [])
            if not videos:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home()); return

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

        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"⚠️ Ошибка генерации: {e}\n\nПопробуйте ещё раз.", reply_markup=kb_home())
        finally:
            try: await msg.delete()
            except: pass
        return

    # Пост-кнопки после видео
    if data == "edit_from_last":
        # Возвращаемся к редактированию текущей сцены
        st["awaiting_scene"] = True
        await q.message.reply_text("✏️ Отправьте новый текст сцены. Текущая версия ниже.")
        await q.message.reply_text(f"Текущая сцена:\n\n{st.get('scene','')}", reply_markup=kb_back_only())
        return

    # fallback
    await q.message.reply_text("Команда пока не поддерживается. Возврат в меню.", reply_markup=kb_home())

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

