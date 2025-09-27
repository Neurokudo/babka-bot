# main.py – меню, помощник, NEUROKUDO, мем-рандом, стили, реплика, генерация Veo
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

# --- Модель OpenAI (дефолт gpt-4o-mini) ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
# Страховка: если по ошибке указали gemini – форсим gpt-4o-mini
if "gemini" in OPENAI_MODEL.lower():
    OPENAI_MODEL = "gpt-4o-mini"

DEFAULT_STYLE = "Кино"
DEFAULT_ORIENTATION = "9:16"  # по умолчанию вертикальное

# ========= OPENAI (GPT) =========
from openai import OpenAI
gpt: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        gpt = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI GPT активирован.")
        log.info(f"Модель: {OPENAI_MODEL}")
    except Exception as e:
        log.error("OpenAI init error: %s", e)

def _sanitize(text: str) -> str:
    if not text:
        return text
    text = text.replace('"', '')
    text = text.replace("'", '')
    text = text.replace('-', '')
    text = text.replace('_', ' ')
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
            temperature=temperature,
            max_tokens=max_tokens,
        )
        out = (r.choices[0].message.content or "").strip()
        return _sanitize(out)
    except Exception as e:
        log.error("GPT error: %s", e)
        return None

# – Сцена на ~8 сек, максимум 2 смены плана, без поэзии
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "complex": "Добавь больше деталей, сделай сцену насыщеннее и сложнее визуально.",
        "simple": "Сделай сцену проще, убери лишние детали, оставь только главное.",
        "absurd": "Сделай сцену более абсурдной и смешной."
    }.get(mode, "Сделай рабочую сцену.")
    
    sys = (
        "Ты редактор коротких видеосцен. "
        "Формулируй именно СЦЕНУ: кто где что делает. "
        "Длительность примерно 8 секунд, максимум две смены плана. "
        "Только действие и визуальные детали, без поэтических эмоций. "
        "Запрещены текст/субтитры/водяные знаки в кадре. "
        "СТРОГО не используй кавычки и тире в тексте. "
        f"{style} Напиши 1–2 коротких предложения."
    )
    temp = 0.65 if mode == "normal" else 0.85 if mode == "complex" else 0.55 if mode == "simple" else 0.9
    out = _gpt(sys, user_text, temperature=temp, max_tokens=140)
    return out or _sanitize(user_text)

def suggest_replica(scene: str) -> Optional[str]:
    sys = "Придумай короткую реплику героя к сцене, 4–10 слов. Только сама фраза. ЗАПРЕЩЕНЫ кавычки, тире, двоеточия, точка с запятой. Можно только запятые, точки, восклицательный и вопросительный знаки."
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ========= NEUROKUDO режим =========

def generate_nkudo_single_scene() -> str:
    sys = (
        "Ты создаешь сцены в стиле NEUROKUDO: обычный российский быт встречается с необычным объектом. "
        "ВАЖНО: сцена должна быть реалистичной для съемки, НЕ фантастической. "
        "Придумай ОДНУ сцену длительностью 8 секунд где обычная бабушка или дед взаимодействует с необычным но РЕАЛЬНЫМ объектом. "
        "Примеры хорошего: бабушка кормит страуса на балконе, дед выгуливает альпаку во дворе, "
        "бабушка моет слоненка в ванной, дед учит попугая ара читать газету. "
        "НЕ придумывай: порталы, динозавров, инопланетян, фантастику. "
        "Формат: простое бытовое действие с необычным животным или предметом. "
        "Никаких кавычек, тире. Напиши 1-2 предложения."
    )
    usr = "Сгенерируй сцену где обычный быт встречается с необычным объектом."
    return _gpt(sys, usr, temperature=0.75, max_tokens=100) or "Бабушка расчесывает ламу на кухне пятиэтажки"

def generate_nkudo_reportage() -> tuple[str, str, str]:
    sys1 = (
        "Ты создаешь новостной репортаж в стиле NEUROKUDO. "
        "Придумай ПЕРВУЮ сцену (8 секунд): журналистка с микрофоном говорит ОДНУ короткую фразу "
        "типа 'Пенсионерка из Запупинска завела носорога'. "
        "На заднем плане бабушка с этим необычным но РЕАЛЬНЫМ животным или объектом. "
        "Примеры: бабушка с ламой, дед с павлином, бабушка с огромным кактусом. "
        "НЕ фантастика! Реальные животные и предметы. "
        "Опиши: фраза журналистки (5-8 слов) + что на фоне. "
        "ЗАПРЕЩЕНЫ кавычки, тире, двоеточия. 1-2 предложения."
    )
    scene1 = _gpt(sys1, "Создай сцену репортажа", temperature=0.7, max_tokens=100)

    sys2 = (
        "Придумай ВТОРУЮ сцену репортажа (8 секунд): крупный план бабушки. "
        "Она объясняет ситуацию и в конце говорит короткую фразу-бомбу. "
        "Стиль: деревенский юмор, прямота, без мата. "
        "Финальная фраза типа: 'Чего уставились', 'Вот и весь сказ', 'Ну и ладно'. "
        "ЗАПРЕЩЕНЫ тире, двоеточия, точка с заяпятой, кавычки. "
        "Опиши сцену с её объяснением и финальной фразой. 2-3 предложения."
    )
    scene2 = _gpt(sys2, f"Контекст: {scene1}", temperature=0.75, max_tokens=120)
    replica = "Чего смотрите то"

    return (
        scene1 or "Журналистка говорит что пенсионерка завела ламу. На фоне бабушка чешет ламу",
        scene2 or "Бабушка объясняет что лама лучше собаки сторожит огород и говорит: Чего смотрите то",
        replica
    )

from veo_client import generate_video_sync

# ========= СЕКРЕТНЫЙ JSON-КОНВЕРТЕР =========
def to_json_prompt(scene: str, style: Optional[str], replica: Optional[str], mode: Optional[str]) -> str:
    """
    Если пользователь прислал уже JSON — не трогаем.
    Иначе GPT конвертит сцену+стиль+реплику в JSON-структуру для Veo.
    """
    try:
        json.loads(scene)
        return scene
    except Exception:
        pass

    if not gpt:
        # Фолбэк — возвращаем как есть
        return scene

    sys = (
        "Ты промт-инженер для Google Veo 3.0. "
        "Возьми описание сцены, стиль и реплику, и преврати в JSON промт строго в такой структуре: "
        "{shot:{composition, camera_motion, lens, frame_rate, film_grain}, "
        " environment:{location, time_of_day, weather}, "
        " characters:[{name, position, appearance, action}], "
        " dialogue:[{character, voice, line}], "
        " lighting, ambient, mood, constraints}. "
        "Всегда заполняй поля осмысленными значениями. Реплику перенеси в dialogue. "
        "Запрещены субтитры/текст в кадре."
    )
    if mode == "nkudo":
        sys += " Стиль: бытовуха + необычный объект, реализм, лёгкий юмор."
    elif mode == "reportage":
        sys += " Формат: новостной репортаж. Сцена 1 — журналистка говорит, сцена 2 — бабушка отвечает."
    elif mode == "meme":
        sys += " Сделай гротескно и смешно, но реалистично снимаемо."
    else:
        sys += " Сделай съёмочную сцену с реалистичными действиями."

    usr = f"Сцена: {scene}\nСтиль: {style or ''}\nРеплика: {replica or ''}"

    try:
        r = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": usr}],
            temperature=0.6,
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
            "editing_scene": None,
            "scene_backup": None,
            "orientation": DEFAULT_ORIENTATION,  # добавили ориентацию
            "nkudo_type": None,
            "nkudo_scene1": None,
            "nkudo_scene2": None,
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
        [InlineKeyboardButton("🔮 Как у NEUROKUDO", callback_data="mode_nkudo")],
        [InlineKeyboardButton("✏️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Усложни", callback_data="var_complex"),
         InlineKeyboardButton("✂️ Упрости", callback_data="var_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
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
        [InlineKeyboardButton("🚀 Создать видео", callback_data="show_final")],
    ])

def kb_after_replica():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая реплика", callback_data="new_replica")],
        [InlineKeyboardButton("👁 Посмотреть промпт", callback_data="show_final")]
    ])

def kb_final_prompt():
    return InlineKeyboardMarkup([
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
    ])

# ========= МЕМНЫЙ РЕЖИМ =========
def random_meme_scene() -> str:
    subjects = [
        "Бабка", "Дед", "Тётка с авоськой", "Дворник", "Курьер",
        "Официант", "Школьник с рюкзаком", "Рокер", "Бизнес леди", "Мужик в телогрейке"
    ]
    locations = [
        "у подъезда", "на рынке", "в метро", "на остановке",
        "в парке", "во дворе панельного дома", "на набережной", "у киоска с шаурмой"
    ]
    props = [
        "арбузом", "самоваром", "гигантским пакетом чипсов", "надувным крокодилом",
        "плюшевым медведем", "огромной лампой торшером", "портретом кота", "резиновым утёнком"
    ]
    items_plural = [
        "апельсинами", "булочками", "плюшевыми утками", "сосисками в тесте",
        "листовками", "ладошками из поролона", "магнитиками", "стеклянными банками"
    ]
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

    import random as _rnd
    t = _rnd.choice(templates)
    s = _rnd.choice(subjects)
    loc = _rnd.choice(locations)

    if "{veh}" in t:
        txt = t.format(s=s, veh=_rnd.choice(vehicles), loc=loc)
    elif "{npc}" in t:
        txt = t.format(s=s, npc=_rnd.choice(npcs), loc=loc)
    elif "{items}" in t:
        txt = t.format(s=s, items=_rnd.choice(items_plural), loc=loc)
    else:
        txt = t.format(s=s, prop=_rnd.choice(props), loc=loc)

    return _sanitize(txt)

# ========= ХЭНДЛЕРЫ =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    users[uid].update({
        "mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
        "awaiting_scene": False, "awaiting_custom_style": False, "awaiting_scene_edit": False
    })
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_home())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    if st.get("awaiting_scene_edit"):
        editing = st.get("editing_scene")
        if editing == 1:
            st["nkudo_scene1"] = text
            await update.message.reply_text("✅ Сцена 1 обновлена!")
        elif editing == 2:
            st["nkudo_scene2"] = text
            await update.message.reply_text("✅ Сцена 2 обновлена!")
        st["awaiting_scene_edit"] = False
        result_text = (
            "📮 Текущий репортаж:\n\n"
            f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n"
            f"🎤 Сцена 2: {st.get('nkudo_scene2', '')}\n\n"
            f"💬 Реплика: {st.get('replica', '')}"
        )
        await update.message.reply_text(result_text, reply_markup=kb_nkudo_reportage_edit())
        return

    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"✅ Выбран стиль: {st['style']}")
        await update.message.reply_text("Что делаем дальше?", reply_markup=kb_after_style())
        return

    if st["awaiting_scene"]:
        st["awaiting_scene"] = False
        st["source_text"] = text
        if st["mode"] == "helper" and gpt:
            scene = improve_scene(text, mode="normal")
            st["scene"] = scene
            await update.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{scene}", reply_markup=kb_variants())
            return
        st["scene"] = text
        await update.message.reply_text(f"📝 Промт принят:\n\n{text}", reply_markup=kb_variants())
        return

    await update.message.reply_text("Главное меню:", reply_markup=kb_home())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    _ensure(uid)
    st = users[uid]
    data = q.data
    log.info("Button: %s", data)

    # Меню
    if data == "menu_make":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await q.message.edit_text("🖼️ Оживление изображения: пришлите фото и короткий промт (в разработке)."); return
    if data == "menu_guides":
        await q.message.edit_text("📚 Гайды и оплата – скоро тут ❤️"); return
    if data == "menu_profile":
        await q.message.edit_text("👤 Профиль/Баланс – скоро доступно."); return
    if data == "back_home":
        await q.message.edit_text("Главное меню:", reply_markup=kb_home()); return

    # Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("🧠✨ Режим умного помощника активирован!")
        await q.message.reply_text("Опиши сцену – сделаю её съёмочной на ~8 секунд.")
        return
    if data == "mode_manual":
        st.update({"mode": "manual", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("✏️ Режим ручного ввода активирован!")
        await q.message.reply_text("Введи свою сцену (я ничего не меняю).")
        return
    if data == "mode_meme":
        st.update({"mode": "meme", "style": None, "replica": None})
        scene = random_meme_scene()
        st["scene"] = scene
        await q.message.edit_text("🎲 Мемный режим активирован!")
        await q.message.reply_text(f"🎭 Случайная сцена:\n\n{scene}", reply_markup=kb_meme())
        return
    if data == "mode_nkudo":
        st.update({"mode": "nkudo", "scene": None, "style": None, "replica": None})
        await q.message.edit_text("🔮 Режим «Как у NEUROKUDO» активирован!")
        explanation = (
            "🔮 Экспериментальный режим создания сцен и репортажей в стиле NEUROKUDO!\n\n"
            "Сочетание обычного быта с необычными объектами.\n\n"
            "Выберите тип сюжета:"
        )
        await q.message.reply_text(explanation, reply_markup=kb_nkudo_menu())
        return
    if data == "back_modes":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return

    # NEUROKUDO
    if data == "nkudo_menu_back":
        await q.message.edit_text("Выберите тип сюжета:", reply_markup=kb_nkudo_menu()); return
    if data == "nkudo_single":
        await q.message.edit_text("⏳ Генерирую сцену...")
        scene = generate_nkudo_single_scene()
        st["scene"] = scene
        st["nkudo_type"] = "single"
        txt = "🔮 Сгенерирована сцена в стиле NEUROKUDO\n\n🎬 Сцена (8 сек):\n" + scene + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_single()); return
    if data == "nkudo_regenerate_single":
        await q.message.edit_text("🔄 Генерирую новую сцену...")
        scene = generate_nkudo_single_scene()
        st["scene"] = scene
        txt = "🔮 Новая сцена сгенерирована\n\n🎬 Сцена (8 сек):\n" + scene + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_single()); return
    if data == "nkudo_improve_single":
        if st.get("scene"):
            st["scene_backup"] = st["scene"]
            improved = improve_scene(st["scene"], mode="complex")
            st["scene"] = improved
            txt = "🧠✨ Сцена улучшена помощником\n\n🎬 Улучшенная сцена:\n" + improved + "\n\nОставить улучшенную версию?"
            await q.message.edit_text(txt, reply_markup=kb_improve_confirm())
        return
    if data == "nkudo_reportage":
        await q.message.edit_text("⏳ Генерирую репортаж из деревни...")
        scene1, scene2, replica = generate_nkudo_reportage()
        st["nkudo_scene1"] = scene1
        st["nkudo_scene2"] = f"{scene2} и говорит: {replica}" if replica and " говорит:" not in scene2 else scene2
        st["replica"] = replica
        st["scene"] = f"{scene1}\n\n{st['nkudo_scene2']}"
        st["nkudo_type"] = "reportage"
        txt = (
            "🔮 Сгенерирован репортаж в стиле NEUROKUDO\n\n"
            "📺 Сцена 1 (Репортаж - 8 сек):\n" + scene1 + "\n\n"
            "🎤 Сцена 2 (Интервью - 8 сек):\n" + st["nkudo_scene2"] + "\n\n"
            "Общая длительность: 16 секунд"
        )
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_edit_scene1":
        st["editing_scene"] = 1
        st["awaiting_scene_edit"] = True
        await q.message.reply_text(
            f"✏️ Редактирование сцены 1:\n\n{st.get('nkudo_scene1', '')}\n\n"
            "Отправьте новый текст сцены или нажмите отмену:",
            reply_markup=kb_scene_edit()
        ); return

    if data == "nkudo_edit_scene2":
        st["editing_scene"] = 2
        st["awaiting_scene_edit"] = True
        await q.message.reply_text(
            f"✏️ Редактирование сцены 2:\n\n{st.get('nkudo_scene2', '')}\n\n"
            "Отправьте новый текст сцены или нажмите отмену:",
            reply_markup=kb_scene_edit()
        ); return

    if data == "scene_save":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("✅ Изменения сохранены!")
        txt = (
            "📮 Текущий репортаж:\n\n"
            f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n"
            f"🎤 Сцена 2: {st.get('nkudo_scene2', '')}\n\n"
            f"💬 Реплика: {st.get('replica', '')}"
        )
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "scene_cancel":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("❌ Редактирование отменено")
        txt = (
            "📮 Текущий репортаж:\n\n"
            f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n"
            f"🎤 Сцена 2: {st.get('nkudo_scene2', '')}\n\n"
            f"💬 Реплика: {st.get('replica', '')}"
        )
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_new_replica":
        sys = (
            "Придумай короткую финальную фразу бабушки для репортажа. "
            "Стиль: народная мудрость с юмором. "
            "Примеры: 'Чего уставились', 'Вот и весь сказ', 'Ну и ладно'. "
            "3-6 слов. ЗАПРЕЩЕНЫ кавычки, тире, двоеточия, точка с заяпятой."
        )
        new_replica = _gpt(sys, f"Контекст: {st.get('nkudo_scene2', '')}", temperature=0.8, max_tokens=25) or "Поехали уже"
        st["replica"] = new_replica
        scene2_base = st.get("nkudo_scene2", "")
        if " и говорит:" in scene2_base or " говорит:" in scene2_base:
            scene2_base = scene2_base.split(" и говорит:")[0].split(" говорит:")[0]
        st["nkudo_scene2"] = f"{scene2_base} и говорит: {new_replica}"
        st["scene"] = f"{st.get('nkudo_scene1', '')}\n\n{st['nkudo_scene2']}"
        txt = "💬 Новая реплика сгенерирована!\n\n" + f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n" + f"🎤 Сцена 2: {st['nkudo_scene2']}"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_regenerate_report":
        await q.message.edit_text("🔄 Генерирую новый репортаж...")
        scene1, scene2, replica = generate_nkudo_reportage()
        st["nkudo_scene1"] = scene1
        st["nkudo_scene2"] = f"{scene2} и говорит: {replica}" if replica and " говорит:" not in scene2 else scene2
        st["replica"] = replica
        st["scene"] = f"{scene1}\n\n{st['nkudo_scene2']}"
        txt = "🔮 Новый репортаж сгенерирован\n\n" + f"📺 Сцена 1: {scene1}\n\n" + f"🎤 Сцена 2: {st['nkudo_scene2']}"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_improve_report":
        if st.get("nkudo_scene1") and st.get("nkudo_scene2"):
            st["scene1_backup"] = st["nkudo_scene1"]
            st["scene2_backup"] = st["nkudo_scene2"]
            scene1_improved = improve_scene(st["nkudo_scene1"], mode="complex")
            scene2_improved = improve_scene(st["nkudo_scene2"], mode="normal")
            st["nkudo_scene1"] = scene1_improved
            st["nkudo_scene2"] = scene2_improved
            st["scene"] = f"{scene1_improved}\n\n{scene2_improved}"
            txt = (
                "🧠✨ Сцены улучшены помощником:\n\n"
                f"📺 Сцена 1: {scene1_improved}\n\n"
                f"🎤 Сцена 2: {scene2_improved}\n\n"
                f"💬 Реплика: {st.get('replica', '')}\n\n"
                "Оставить улучшенную версию?"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оставить улучшенное", callback_data="report_improve_keep")],
                [InlineKeyboardButton("↩️ Отмена (вернуть прежнее)", callback_data="report_improve_cancel")],
            ])
            await q.message.edit_text(txt, reply_markup=kb)
        return

    if data == "improve_keep":
        st["scene_backup"] = None
        await q.message.edit_text("✅ Улучшенная версия сохранена!")
        if st.get("nkudo_type") == "single":
            txt = f"🎬 Сцена (8 сек):\n{st['scene']}\n\nЧто делаем дальше?"
            await q.message.reply_text(txt, reply_markup=kb_nkudo_single())
        return

    if data == "improve_cancel":
        if st.get("scene_backup"):
            st["scene"] = st["scene_backup"]
            st["scene_backup"] = None
            await q.message.edit_text("↩️ Возвращена прежняя версия!")
            txt = f"🎬 Сцена (8 сек):\n{st['scene']}\n\nЧто делаем дальше?"
            await q.message.reply_text(txt, reply_markup=kb_nkudo_single())
        return

    if data == "improve_again":
        if st.get("scene"):
            improved = improve_scene(st["scene"], mode="complex")
            st["scene"] = improved
            txt = "🧠✨ Сцена улучшена ещё раз\n\n" + f"🎬 Улучшенная сцена:\n{improved}\n\n" + "Оставить эту версию?"
            await q.message.edit_text(txt, reply_markup=kb_improve_confirm())
        return

    if data == "report_improve_keep":
        st["scene1_backup"] = None
        st["scene2_backup"] = None
        await q.message.edit_text("✅ Улучшенная версия сохранена!")
        txt = (
            "📮 Текущий репортаж:\n\n"
            f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n"
            f"🎤 Сцена 2: {st.get('nkudo_scene2', '')}\n\n"
            f"💬 Реплика: {st.get('replica', '')}"
        )
        await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "report_improve_cancel":
        if st.get("scene1_backup") and st.get("scene2_backup"):
            st["nkudo_scene1"] = st["scene1_backup"]
            st["nkudo_scene2"] = st["scene2_backup"]
            st["scene"] = f"{st['scene1_backup']}\n\n{st['scene2_backup']}"
            st["scene1_backup"] = None
            st["scene2_backup"] = None
            await q.message.edit_text("↩️ Возвращена прежняя версия!")
            txt = (
                "📮 Текущий репортаж:\n\n"
                f"📺 Сцена 1: {st.get('nkudo_scene1', '')}\n\n"
                f"🎤 Сцена 2: {st.get('nkudo_scene2', '')}\n\n"
                f"💬 Реплика: {st.get('replica', '')}"
            )
            await q.message.reply_text(txt, reply_markup=kb_nkudo_reportage_edit())
        return

    if data == "nkudo_approve":
        if st.get("nkudo_type") == "reportage":
            st["style"] = "Документальный"
            await q.message.edit_text(
                "✅ Сюжет утвержден!\n\n"
                "📺 Общая длительность: 16 секунд (2 сцены по 8 сек)\n"
                "🎨 Стиль: Документальный репортаж\n\n"
                "Готово к генерации видео!"
            )
            # Перед генерацией спросим ориентацию
            await q.message.reply_text("Выбери ориентацию:", reply_markup=kb_orientation())
            # И подготовим финальный шаг
            await q.message.reply_text("📝 Итоговый промпт готов. Жмём запуск, когда определишься с ориентацией.",
                                       reply_markup=kb_final_prompt())
        return

    # Варианты улучшения
    if data == "var_complex":
        if st.get("source_text") and gpt:
            scene = improve_scene(st["source_text"], mode="complex")
            st["scene"] = scene
            await q.message.edit_text(f"🔍 Усложнено:\n\n{scene}", reply_markup=kb_variants())
        return
    if data == "var_simple":
        if st.get("source_text") and gpt:
            scene = improve_scene(st["source_text"], mode="simple")
            st["scene"] = scene
            await q.message.edit_text(f"✂️ Упрощено:\n\n{scene}", reply_markup=kb_variants())
        return
    if data == "var_again":
        if st.get("source_text") and gpt:
            scene = improve_scene(st["source_text"], mode="normal")
            st["scene"] = scene
            await q.message.edit_text(f"🔄 Переделано:\n\n{scene}", reply_markup=kb_variants())
        return

    # Переход к стилям
    if data in ("go_next", "choose_style"):
        if st.get("scene"):
            await q.message.edit_text(f"✅ Сцена готова:\n\n{st['scene']}")
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles())
        return

    if data.startswith("style_"):
        val = data.split("_", 1)[1]
        if val == "custom":
            st["awaiting_custom_style"] = True
            await q.message.edit_text("✏️ Напишите желаемый стиль для видео:")
            return
        st["style"] = None if val == "None" else val
        style_text = st['style'] or "Без стиля"
        await q.message.edit_text(f"✅ Выбран стиль: {style_text}")
        await q.message.reply_text("Что делаем дальше?", reply_markup=kb_after_style())
        return

    if data == "add_replica" or data == "new_replica":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        text = suggest_replica(st["scene"]) or "Поехали уже!"
        st["replica"] = text
        if data == "new_replica":
            await q.message.edit_text(f"✅ Создана реплика: {text}", reply_markup=kb_after_replica())
        else:
            await q.message.edit_text(f"✅ Создана реплика: {text}")
            await q.message.reply_text("Готово! Можно генерировать другую реплику или смотреть промпт.", reply_markup=kb_after_replica())
        return

    if data == "show_final":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        final_text = "📝 Итоговый промпт:\n\n"
        final_text += f"🎬 Сцена: {st['scene']}\n\n"
        if st.get("style"):
            final_text += f"🎨 Стиль: {st['style']}\n\n"
        if st.get("replica"):
            final_text += f"💬 Реплика: {st['replica']}\n\n"
        final_text += "Всё готово для генерации!"
        await q.message.reply_text(final_text)
        # Перед запуском — выбор ориентации
        await q.message.reply_text("Выбери ориентацию:", reply_markup=kb_orientation())
        await q.message.reply_text("Когда готов — запускаем:", reply_markup=kb_final_prompt())
        return

    # ==== ОРИЕНТАЦИЯ ====
    if data == "ori_916":
        st["orientation"] = "9:16"
        await q.message.edit_text("✅ Ориентация: Вертикальное (9:16)")
        return
    if data == "ori_169":
        st["orientation"] = "16:9"
        await q.message.edit_text("✅ Ориентация: Горизонтальное (16:9)")
        return

    # ==== ГЕНЕРАЦИЯ ВИДЕО (Veo) ====
    if data == "generate_now":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None:
            st["style"] = DEFAULT_STYLE
        if not st.get("orientation"):
            st["orientation"] = DEFAULT_ORIENTATION

        try:
            await q.message.edit_reply_markup(reply_markup=None)
        except:
            pass

        msg = await q.message.reply_text("⏳ Генерирую видео… Это может занять несколько минут.")
        try:
            mode = st.get("mode")

            # Репортаж → два видео подряд (по 8 сек)
            if st.get("nkudo_type") == "reportage" or mode == "reportage":
                # Сцена 1
                prompt1 = to_json_prompt(st.get("nkudo_scene1",""), st.get("style"), None, "reportage")
                res1 = await asyncio.to_thread(
                    generate_video_sync,
                    prompt1,
                    duration=8,
                    aspect_ratio=st["orientation"]
                )
                vids1 = (res1 or {}).get("videos", [])
                if not vids1:
                    await q.message.reply_text("⚠️ Сцена 1: видео не вернулось.")
                else:
                    v1 = vids1[0]
                    if v1.get("file_path") and os.path.exists(v1["file_path"]):
                        with open(v1["file_path"], "rb") as f:
                            await q.message.reply_video(video=f, caption="📺 Сцена 1", supports_streaming=True)
                    elif v1.get("uri"):
                        await q.message.reply_text(f"📺 Сцена 1 (GCS): {v1['uri']}")

                # Сцена 2
                prompt2 = to_json_prompt(st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage")
                res2 = await asyncio.to_thread(
                    generate_video_sync,
                    prompt2,
                    duration=8,
                    aspect_ratio=st["orientation"]
                )
                vids2 = (res2 or {}).get("videos", [])
                if not vids2:
                    await q.message.reply_text("⚠️ Сцена 2: видео не вернулось.")
                else:
                    v2 = vids2[0]
                    cap2 = "🎤 Сцена 2" + (f"\n💬 {st.get('replica')}" if st.get("replica") else "")
                    if v2.get("file_path") and os.path.exists(v2["file_path"]):
                        with open(v2["file_path"], "rb") as f:
                            await q.message.reply_video(video=f, caption=cap2, supports_streaming=True)
                    elif v2.get("uri"):
                        await q.message.reply_text(f"{cap2}\n\nGCS: {v2['uri']}")

                await q.message.reply_text("Готово! Хотите создать ещё одно видео?", reply_markup=kb_home())
                return

            # Все остальные режимы → одно видео
            prompt = to_json_prompt(st["scene"], st.get("style"), st.get("replica"), st.get("mode"))
            res = await asyncio.to_thread(
                generate_video_sync,
                prompt,
                duration=8,
                aspect_ratio=st["orientation"]
            )

            videos = (res or {}).get("videos", [])
            if not videos:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home())
                return

            v0 = videos[0]
            file_path = v0.get("file_path")
            uri = v0.get("uri")

            caption = (
                f"✅ Видео готово!\n\n"
                f"🎬 Сцена: {st['scene']}\n"
                f"🎨 Стиль: {st['style']}"
                + (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "")
                + (f"\n📐 Ориентация: {st['orientation']}" if st.get("orientation") else "")
            )

            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await q.message.reply_video(video=f, caption=caption, supports_streaming=True)
            elif uri:
                # Фолбэк: если не скачалось — хотя бы даём ссылку GCS
                await q.message.reply_text(f"{caption}\n\n🔗 Ссылка на видео (GCS): {uri}")
            else:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home())

            await q.message.reply_text("Хотите создать ещё одно видео?", reply_markup=kb_home())

        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"⚠️ Ошибка генерации: {e}\n\nПопробуйте ещё раз.", reply_markup=kb_home())
        finally:
            try:
                await msg.delete()
            except Exception:
                pass
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

