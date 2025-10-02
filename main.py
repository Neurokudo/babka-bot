# main.py — версия с детальными стилями и разделом «🧾 JSON (для продвинутых)».
# Ключевые изменения:
# 1) Новый STYLE_HINTS + style_instructions() — стили описаны для героя, одежды, материалов, окружения, палитры, света, камеры, поста.
# 2) В _rich_json_template() добавлена жёсткая инструкция: «встраивай style_directives в subject.description, scene, lighting, mood и shot».
# 3) В обычных режимах (помощник/нейрокудо/мемы) показ JSON пользователю УБРАН.
# 4) Добавлен отдельный раздел «🧾 JSON (для продвинутых)»: ввод текста → генерация JSON → выбор ориентации → кнопка «Сгенерировать».
# 5) Все главные кнопки продублированы в Reply-клавиатуре (внизу, с SOS). В инлайн-меню — те же пункты БЕЗ SOS.
# 6) «👗 Виртуальная примерочная» (VTO) + пост-действия: другая поза/другая одежда/новая локация/описать позу.

import os
import json
import random
import asyncio
import logging
import smtplib
import time
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# Импорты для работы с базой данных и биллингом
from database import db

# -----------------------------------------------------------------------------
# ОКРУЖЕНИЕ / ЛОГИ
# -----------------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SMTP для репортов (нижняя кнопка SOS)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER
SUPPORT_TO_EMAIL = "antonkudo.ai@gmail.com"

# (опционально) дублирование репортов в TG-чат(ы)
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

# Доступ только владельцу до релиза
ALLOWED_USERS = [5015100177]

OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
if "gemini" in (OPENAI_MODEL or "").lower():
    OPENAI_MODEL = "gpt-4o-mini"

DEFAULT_STYLE = "Кино"
DEFAULT_ORIENTATION = "9:16"  # по умолчанию вертикалка
DEFAULT_AUDIO = True  # по умолчанию с аудио

# -----------------------------------------------------------------------------
# КОНФИГУРАЦИЯ И БИЛЛИНГ
# -----------------------------------------------------------------------------
from config import (
    COST_VIDEO, COST_TRANSFORM, COST_TRANSFORM_PREMIUM, COST_TRYON,
    FREE_RETRY_PER_JOB, DAILY_CAP_VIDEOS, LOW_COINS_THRESHOLD,
    PLANS, TOP_UPS, ADDONS, IMG_SIZE, QUALITY
)
from payment_yookassa import create_payment_link, process_payment_webhook
from billing import (
    can_spend, hold_and_start, on_success, on_error, retry,
    check_daily_cap, inc_daily_video, get_daily_videos_left,
    check_low_coins, get_retry_cost, can_retry,
    has_video_bonus, has_photo_bonus, can_generate_video, can_generate_photo
)

# -----------------------------------------------------------------------------
# GPT
# -----------------------------------------------------------------------------
from openai import OpenAI
gpt: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        gpt = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI GPT активирован. Модель: %s", OPENAI_MODEL)
    except Exception as e:
        log.error("OpenAI init error: %s", e)
        gpt = None
else:
    log.warning("OPENAI_API_KEY не установлен - GPT функции недоступны")
    gpt = None

def _sanitize(text: str) -> str:
    if not text:
        return text
    for ch in ['—', '–', '«', '»', '"', "'", '“', '”', '„', '‟']:
        text = text.replace(ch, '')
    text = text.replace('-', '').replace('_', ' ')
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _clean_replica(text: str) -> str:
    """Очищает фразу от всех видов тире и дефисов"""
    if not text:
        return text
    # Удаляем все виды тире и дефисов
    for ch in ['—', '–', '-']:
        text = text.replace(ch, '')
    # Удаляем лишние пробелы
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

# -----------------------------------------------------------------------------
# EMAIL + ADMIN NOTIFY
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# ДЕТАЛИЗИРОВАННЫЕ СТИЛИ
# -----------------------------------------------------------------------------
STYLE_HINTS = {
    "Анимэ": {
        "subject": "anime-style characters with cel-shaded outlines, exaggerated expressions, large eyes, simplified textures. Each object drawn in anime style with sharp outlines and flat shading.",
        "scene": "background like hand-painted anime background art with watercolor gradients, flat colors with subtle gradients, pastel palette with saturated highlights.",
        "lighting": "light bloom effects, stylized lighting without realistic shadows, clean highlights.",
        "mood": "Energetic, expressive, colorful.",
        "shot": "Cinematic anime shot, medium-wide, dolly-in, dynamic angles typical of anime films. Add falling petals, glowing city lights, stylized clouds."
    },
    "LEGO": {
        "subject": "EVERYTHING MUST BE MADE OF LEGO BRICKS: grandmother as LEGO minifigure with yellow skin, cylindrical hands, LEGO hair piece, brick-patterned clothing. All objects are LEGO blocks with visible studs and plastic texture.",
        "scene": "Complete LEGO world: ground made of LEGO baseplates, all buildings and objects constructed from LEGO bricks with visible studs and seams. No realistic textures allowed.",
        "lighting": "Bright studio lighting with strong plastic reflections, pure saturated colors typical of LEGO sets, no realistic shadows.",
        "mood": "Playful, toy-like, artificial.",
        "shot": "Low angle as if filming miniatures, smooth camera movements, shallow depth of field to emphasize toy scale."
    },
}

def style_instructions(style_name: Optional[str]) -> str:
    if not style_name or style_name not in STYLE_HINTS:
        return ""
    s = STYLE_HINTS[style_name]
    # Компактная директива стиля на английском для Veo
    return (
        f"{s['subject']} "
        f"{s['scene']} "
        f"Lighting: {s['lighting']}. "
        f"Mood: {s['mood']}. "
        f"Shot: {s['shot']}."
    )

# -----------------------------------------------------------------------------
# СЦЕНАРНЫЕ ХЕЛПЕРЫ
# -----------------------------------------------------------------------------
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "complex": "Добавь деталей, сделай сцену насыщеннее и визуально сложнее.",
        "simple": "Упрости сцену, оставь только главное.",
        "absurd": "Сделай сцену более абсурдной и смешной."
    }.get(mode, "Сделай рабочую сцену.")
    sys = (
        "Ты редактор коротких видеосцен. Формулируй именно ОДНУ СЦЕНУ: кто где что делает. "
        "Длительность ~8 секунд, ОДНА сцена без разделения на части. Без поэзии/оценок. "
        "Субтитры и текст в кадре запрещены. Не используй кавычки и тире. "
        "НЕ создавай несколько сцен или сцен 1/2. Только ОДНА цельная сцена. "
        f"{style} Напиши 1–2 коротких предложения, описывающих ОДНУ сцену."
    )
    temp = {"normal": 0.65, "complex": 0.85, "simple": 0.55, "absurd": 0.9}[mode]
    return _gpt(sys, user_text, temperature=temp, max_tokens=140) or _sanitize(user_text)

def improve_scene_with_phrase(scene_text: str, phrase: str, mode: str = "complex") -> str:
    """Улучшает сцену, сохраняя фразу"""
    if not phrase:
        return improve_scene(scene_text, mode)
    
    # Извлекаем фразу из сцены, если она там есть
    import re
    # Ищем фразу в кавычках
    quote_pattern = r'"[^"]*"'
    scene_without_phrase = re.sub(quote_pattern, '', scene_text).strip()
    
    # Улучшаем сцену без фразы
    improved_scene = improve_scene(scene_without_phrase, mode)
    
    # Встраиваем фразу обратно
    embed_prompt = (
        f"Встрой фразу в улучшенное описание сцены как речь персонажа.\n\n"
        f"Улучшенная сцена: {improved_scene}\n"
        f"Фраза: {phrase}\n\n"
        f"ТРЕБОВАНИЯ:\n"
        f"- Встрой фразу как прямую речь персонажа в кавычках\n"
        f"- Добавь слова автора типа 'говорит', 'восклицает', 'шепчет' и т.д.\n"
        f"- Фраза должна звучать естественно в контексте сцены\n"
        f"- Сцена должна остаться целостной и логичной\n"
        f"- НЕ добавляй никаких технических деталей, стилей, ориентаций\n"
        f"- НЕ добавляй строки типа 'Style:', 'Replica:', 'Orientation:'\n\n"
        f"Верни ТОЛЬКО обновленное описание сцены без дополнительных комментариев."
    )
    
    try:
        if not gpt:

            replica = "Да сама довезу без принцев обойдусь!"

        else:

            resp = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": embed_prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        result = resp.choices[0].message.content.strip() if resp else ""
        
        # Очищаем результат от лишних строк
        lines = result.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Пропускаем строки с техническими деталями
            if (line.startswith('- Style:') or 
                line.startswith('- Replica:') or 
                line.startswith('- Orientation:') or
                line.startswith('Style:') or 
                line.startswith('Replica:') or 
                line.startswith('Orientation:') or
                line == '-' or
                line == ''):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    except Exception as e:
        # Если не удалось встроить через GPT, просто добавляем в конец
        return f"{improved_scene}\n\nБабушка говорит: {phrase}"

def suggest_replica(scene: str) -> Optional[str]:
    sys = ("Придумай короткую фразу героя к сцене, 4–10 слов. Только сама фраза. "
           "Запрещены кавычки/тире/двоеточия/точка с запятой.")
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# -----------------------------------------------------------------------------
# NEUROKUDO
# -----------------------------------------------------------------------------
def generate_nkudo_single_scene() -> str:
    sys = (
        "Ты — генератор односценовых видео (ровно 8 секунд) в стиле Neurokudo: тёплый деревенский реализм + одна абсурдная деталь.\n"
        "Всегда выдай одну сцену на русском в ПОВЕСТВОВАТЕЛЬНОМ формате (никакого JSON, никаких заголовков).\n"
        "Запреты: нет репортёров, нет микрофонов, нет титров/водяных знаков/логотипов; не используй слово «Залупинск».\n"
        "Сцена = бабка, объект, простое действие, одна короткая фраза. Хук виден в первые 2-3 секунды.\n"
        "Камера: handheld, на уровне плеч, лёгкая естественная тряска. Свет естественный. Музыки нет; только деревенский амбиент + звуки действия.\n"
        "Героиня: пожилая женщина 75-80 лет, деревенская, 1-2 узнаваемых атрибута (халат/платок/сапоги/эмалированное ведро).\n"
        "Речь: до 20-25 слов, разговорная, с коротким пуантом на конце.\n"
        "Одна задача в кадре, без монтажных склеек и без акробатики камерами.\n\n"
        "ФОРМАТ ОТВЕТА: Повествовательное описание сцены в одном абзаце.\n\n"
        "Примеры (как должен отвечать GPT):\n\n"
        "Пример 1\n"
        "Пенсионерка во дворе деревенского дома толкает гигантскую тыкву-«карету», поправляет платок и хмыкает: «Да сама довезу без принцев обойдусь!». Тыква кренится на бок, и бабка едва не падает.\n\n"
        "Пример 2\n"
        "Старушка в клетчатом халате стоит у огорода рядом с огромным блестящим самоваром, натирает его щёткой и ворчит: «Чайку накипячу душу согрею, не спину». Самовар внезапно громко свистит, бабка отскакивает.\n\n"
        "Пример 3\n"
        "Пожилая женщина в спортивных штанах и жилетке проверяет воду в надувном бассейне, где плавает розовый фламинго размером с лодку. Она усмехается: «Кто без круга тот с гордостью плывёт!». Фламинго резко наклоняется, и бабка чуть не падает в воду.\n\n"
        "Создай новую сцену в стиле NEUROKUDO в повествовательном формате:"
    )
    return _gpt(sys, "Создай новую сцену в стиле NEUROKUDO на русском языке", temperature=0.75, max_tokens=200) or \
           "Пенсионерка во дворе деревенского дома толкает гигантскую тыкву-«карету», поправляет платок и хмыкает: «Да сама довезу без принцев обойдусь!». Тыква кренится на бок, и бабка едва не падает."

def generate_nkudo_reportage_scene1() -> str:
    sys = (
        "Репортаж. Сцена 1 (8 сек): русскоязычная журналистка (женщина, 25–40) в деревенском дворе, "
        "говорит короткую фразу в КАМЕРУ по-русски. На заднем плане бабушка с животным, "
        "которое выполняет ПРОСТЫЕ действия: стоит, сидит, ест, спит, плавает, ходит. "
        "Животные БЕЗ ОДЕЖДЫ, только естественные действия. 1–2 предложения. Без кавычек/тире."
    )
    return _gpt(sys, "Создай сцену 1", temperature=0.7, max_tokens=100) or \
           "Журналистка в деревенском дворе говорит в камеру. На фоне бабушка расчёсывает енота"

def generate_nkudo_reportage_scene2(context_scene1: str) -> tuple[str, str]:
    sys = (
        "Репортаж. Сцена 2 (8 сек): крупный план ТОЙ ЖЕ бабушки. Она отвечает по-русски и в конце "
        "говорит короткую финальную фразу-бомбу (3–6 слов). "
        "ВИЗУАЛЬНАЯ КОНТИНУИТИ: те же люди, одежда, двор, предметы/животное — повторить. "
        "Животные выполняют ПРОСТЫЕ действия: стоит, сидит, ест, спит, плавает, ходит. "
        "СТРОГО ЗАПРЕЩЕНО: никаких тире, дефисов или длинных тире (—, -, –) в фразе!"
    )
    s2 = _gpt(sys, f"Контекст (сцена 1): {context_scene1}", temperature=0.75, max_tokens=120) or \
         "Бабушка в том же дворе, рядом енот; отвечает уверенно и говорит: Вот и весь сказ"
    
    # Генерируем фразу отдельно с запретом на тире
    replica_sys = "Короткая финальная фраза бабушки (ОДНО полное предложение, максимум 20 слов). Без кавычек, тире, дефисов, длинных тире (—, -, –) и двоеточий."
    short = _gpt(replica_sys, f"Контекст сцены: {s2}", temperature=0.8, max_tokens=35) or "Вот и весь сказ"
    short = _clean_replica(short)
    
    return s2, short

def generate_nkudo_reportage() -> tuple[str, str, str]:
    s1 = generate_nkudo_reportage_scene1()
    s2, rep = generate_nkudo_reportage_scene2(s1)
    return s1, s2, rep

# LEGO функции генерации
def generate_lego_single_scene() -> str:
    sys = (
        "Ты — генератор односценовых видео (ровно 8 секунд) в стиле LEGO: яркие пластиковые фигурки, "
        "блочная эстетика, детская простота + одна абсурдная деталь.\n"
        "Всегда выдай одну сцену на русском в ПОВЕСТВОВАТЕЛЬНОМ формате (никакого JSON, никаких заголовков).\n"
        "Запреты: нет репортёров, нет микрофонов, нет титров/водяных знаков/логотипов.\n"
        "Сцена = LEGO фигурка бабушки, LEGO объект, простое действие, одна короткая фраза. Хук виден в первые 2-3 секунды.\n"
        "Стиль: пластиковый, блочный, яркий, детский, но с юмором для взрослых.\n"
        "Примеры: 'LEGO бабушка в ярком платке поливает LEGO цветы из LEGO лейки, в которой вместо воды LEGO конфетти'"
    )
    return _gpt(sys, "", temperature=0.8, max_tokens=150) or "LEGO бабушка строит LEGO дом из LEGO кирпичей, но вместо цемента использует LEGO клей."

def generate_lego_reportage_scene1() -> str:
    sys = (
        "LEGO репортаж. Сцена 1 (8 сек): LEGO журналистка (женщина, 25–40) в LEGO дворе, "
        "говорит короткую фразу в КАМЕРУ по-русски. На заднем плане LEGO бабушка с LEGO животным, "
        "которое выполняет ПРОСТЫЕ действия: стоит, сидит, ест, спит, плавает, ходит. "
        "LEGO животные БЕЗ ОДЕЖДЫ, только естественные действия. 1–2 предложения. Без кавычек/тире."
    )
    return _gpt(sys, "", temperature=0.8, max_tokens=100) or "LEGO журналистка в LEGO дворе рассказывает о LEGO бабушке с LEGO котиком."

def generate_lego_reportage_scene2(context_scene1: str) -> tuple[str, str]:
    sys = (
        "LEGO репортаж. Сцена 2 (8 сек): крупный план ТОЙ ЖЕ LEGO бабушки. Она отвечает по-русски и в конце "
        "говорит короткую финальную фразу-бомбу (3–6 слов). "
        "ВИЗУАЛЬНАЯ КОНТИНУИТИ: те же LEGO люди, LEGO одежда, LEGO двор, LEGO предметы/животное — повторить. "
        "LEGO животные выполняют ПРОСТЫЕ действия: стоит, сидит, ест, спит, плавает, ходит. "
        "Формат: описание сцены + фраза бабушки в кавычках. Без тире/двоеточий."
    )
    result = _gpt(sys, f"Контекст сцены 1: {context_scene1}", temperature=0.8, max_tokens=120)
    if not result:
        return "LEGO бабушка сидит на LEGO лавочке с LEGO котиком", "Вот мои LEGO питомцы"
    
    # Парсим результат для извлечения фрази
    if '"' in result:
        parts = result.split('"')
        if len(parts) >= 2:
            scene = parts[0].strip()
            replica = parts[1].strip()
            return scene, replica
    
    return result, "Вот мои LEGO питомцы"

def generate_lego_reportage() -> tuple[str, str, str]:
    s1 = generate_lego_reportage_scene1()
    s2, rep = generate_lego_reportage_scene2(s1)
    return s1, s2, rep

# -----------------------------------------------------------------------------
# ВИДЕО (VEO)
# -----------------------------------------------------------------------------
from veo_client import generate_video_sync

# -----------------------------------------------------------------------------
# ВИРТУАЛЬНАЯ ПРИМЕРОЧНАЯ (VTO + Nano Banana для «пере-постановки»)
# -----------------------------------------------------------------------------
from tryon_client import virtual_tryon   # оставь файл, как присылал ранее
from nano_client import repose_or_relocate  # оставь файл, как присылал ранее

# -----------------------------------------------------------------------------
# ТРАНСФОРМАЦИИ ИЗОБРАЖЕНИЙ
# -----------------------------------------------------------------------------
from transforms_client import process_transform

# -----------------------------------------------------------------------------
# ГЕНЕРАЦИЯ «БОГАТОГО» JSON ДЛЯ VEO
# -----------------------------------------------------------------------------
def _rich_json_template(scene: str, style: Optional[str], replica: Optional[str],
                        mode: Optional[str], aspect_ratio: str, context: Optional[str]) -> str:
    """
    Собираем промт-директиву для GPT, чтобы он вернул ГОТОВЫЙ JSON под Veo.
    ВАЖНО: мы просим ВСТРАИВАТЬ style_directives в subject.description, scene, lighting, mood и shot.
    """
    style_text = style_instructions(style)

    rep_rules = ""
    if mode == "reportage":
        rep_rules = (
            "Reporter must be Russian-speaking female, speak Russian. "
            "No English lines. Scene 1: reporter speaks to camera; grandmother with object/animal behind. "
            "Scene 2: CLOSE on the SAME grandmother in the SAME yard/clothes/object — strict visual continuity; "
            "repeat characters/props/background from scene 1."
        )

    base_rules = (
        "Return VALID JSON only (no comments). "
        "Prohibit any on-screen text/subtitles/logos/watermarks. "
        "Duration strictly 8 seconds. "
        "IMPORTANT: If the scene involves a grandmother (бабушка/бабка), the voice must be described as 'old female voice, 65-80 years old, warm and experienced tone' in the voiceover section."
    )
    
    # Специальные правила для режима NEUROKUDO
    nkudo_rules = ""
    if mode == "nkudo":
        nkudo_rules = (
            "NEUROKUDO STYLE RULES - Use these EXACT examples:\n"
            "LOCATIONS: 'Zalupinsk backyard', 'Soviet kitchen with green wallpaper', 'chicken coop interior', 'muddy yard with puddles'\n"
            "GRANDMOTHER: 'elderly (~75-85 y.o.)', 'blue floral housecoat', 'red headscarf tied under chin', 'rubber boots', 'quilted jacket'\n"
            "CREATURES: SIMPLE and REALISTIC actions only - animals can walk, run, swim, eat, sleep, stand, sit\n"
            "NO CLOTHING on animals - they are naked/natural\n"
            "NO COMPLEX ACTIONS - no acrobatics, dancing, rolling, complex movements\n"
            "GOOD examples: 'whales swimming in pool', 'elephants eating grass', 'crocodiles sleeping', 'penguins standing'\n"
            "BAD examples: 'penguins in boots', 'crocodiles doing acrobatics', 'elephants wearing clothes'\n"
            "DIALOGUE TONE: 'calm, matter-of-fact', 'proud explanation', 'as if normal', 'village accent'\n"
            "VISUAL DETAILS: 'rusty metal frame', 'wooden fence', 'enamel kettle', 'wicker basket', 'straw on floor', 'muddy ground'\n"
            "CAMERA: 'handheld documentary', 'shaky realism', 'close-up on grandmother's face', 'wide shot showing scale'\n"
            "EXAMPLES:\n"
            "- 'elderly Russian grandmother (~78 y.o.) stands proudly in rubber boots, holding metal bucket, gesturing toward whales swimming'\n"
            "- 'grandmother in blue housecoat feeds velociraptors in chicken coop like regular chickens'\n"
            "- 'babushka in quilted jacket calmly explains about dinosaurs standing in her backyard'\n"
    )

    sys = (
        "You are a prompt engineer for Google Veo 3.0.\n"
        f"{base_rules} {rep_rules} {nkudo_rules}\n"
        "CRITICAL: Apply visual styling STRICTLY to ALL visual elements. "
        "Insert style_directives content into these fields: "
        "subject.description, scene.location, lighting, mood and shot (camera).\n"
        "The style MUST be visible in the final video - this is the most important requirement!\n"
        "Apply the style consistently across all visual elements.\n"
        "Use this schema (keys in English; values can be Russian):\n"
        "{\n"
        '  "model": "veo-3.0-fast",\n'
        '  "duration": 8,\n'
        '  "aspect_ratio": "9:16|16:9",\n'
        '  "style_directives": "конкретные указания по виду героя/одежды/материалов/окружения/палитры/света/камеры/поста",\n'
        '  "shot": {"composition": "...", "camera_motion": "...", "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},\n'
        '  "subject": {"description": "... (со стилем)", "voice_sync": false},\n'
        '  "scene": {"location": "... (со стилем)", "time_of_day": "..."},\n'
        '  "action": "what happens in 8s concisely",\n'
        '  "voiceover": {"voice": "...", "line": "..."},\n'
        '  "characters": [{"name":"...", "position":"...", "appearance":"... (со стилем)", "action":"..."}],\n'
        '  "ambient": "fx list",\n'
        '  "lighting": "освещение с учётом стиля",\n'
        '  "mood": "настроение, вытекающее из стиля",\n'
        '  "restrictions": "No text or logos."\n'
        "}\n"
        "Always keep the JSON compact and consistent."
    )

    usr = (
        f"scene_text: {scene}\n"
        f"replica: {replica or ''}\n"
        f"aspect_ratio: {aspect_ratio}\n"
    )
    if style_text:
        usr += f"IMPORTANT: Apply this style to ALL visual elements: {style_text}\n"
        usr += f"Make sure the style is embedded in subject.description, scene.location, lighting, mood, and shot fields.\n"
    if context:
        usr += f"context_for_continuity: {context}\n"

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
        # fallback максимально честный и простой
        style_stub = style_text or ""
        return json.dumps({
            "model": "veo-3.0-fast",
            "duration": 8,
            "aspect_ratio": aspect_ratio,
            "style_directives": style_stub,
            "shot": {"composition": "medium shot (со стилем)", "camera_motion": "static (со стилем)",
                     "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},
            "subject": {"description": f"{_sanitize(scene)} (со стилем: {style_stub})", "voice_sync": False},
            "scene": {"location": "rural yard (со стилем)", "time_of_day": "day"},
            "action": "simple 8 second action",
            "voiceover": {"voice": "female", "line": _sanitize(replica or "")},
            "characters": [],
            "ambient": "light wind, birds",
            "lighting": "natural daylight (с учётом стиля)",
            "mood": "grounded (с учётом стиля)",
            "restrictions": "No text or logos"
        }, ensure_ascii=False)

def _neurokudo_json_parser(scene: str, style: Optional[str], replica: Optional[str],
                          mode: Optional[str], aspect_ratio: str, context: Optional[str] = None) -> str:
    """
    Новый JSON-парсер для Veo 3 в формате, который точно работает.
    Парсит русский текст сцены и конвертирует в строгий JSON формат для VEO 3.
    """
    sys_prompt = (
        "You are a strict parser for Veo 3 video generation.\n"
        "Input: one short paragraph in Russian that describes a single 8-second scene.\n"
        "Output: only valid JSON in English (no explanations, no comments, no text outside JSON).\n\n"
        "JSON Output Format (exactly as shown):\n"
        "{\n"
        '  "shot": {\n'
        '    "composition": "detailed description of the shot composition",\n'
        '    "camera_motion": "tripod-stable, light breeze moving clothing and trees",\n'
        '    "lens": "35mm",\n'
        '    "frame_rate": "24fps",\n'
        '    "film_grain": "clean digital"\n'
        '  },\n'
        '  "environment": {\n'
        '    "location": "Exterior — description of the place",\n'
        '    "time_of_day": "afternoon",\n'
        '    "weather": "sunny, warm, clear skies, gentle breeze"\n'
        '  },\n'
        '  "characters": [\n'
        '    {\n'
        '      "name": "Character name",\n'
        '      "position": "position in frame",\n'
        '      "appearance": "detailed appearance description",\n'
        '      "action": "specific action being performed"\n'
        '    }\n'
        '  ],\n'
        '  "dialogue": [\n'
        '    {\n'
        '      "character": "Character name",\n'
        '      "voice": "voice description",\n'
        '      "line": "Russian dialogue text"\n'
        '    }\n'
        '  ],\n'
        '  "constraints": "Clear video without text or subtitles"\n'
        '}\n\n'
        "Strict Rules:\n"
        "- Always return valid JSON, nothing else\n"
        "- Composition must be detailed and specific (e.g., 'medium wide street-level shot of...')\n"
        "- Characters array must include all people mentioned\n"
        "- Dialogue array must include all speech mentioned\n"
        "- Russian dialogue goes in 'line' field\n"
        "- Maximum 2500 characters total\n"
        "- Extract all objects, actions, and details mentioned\n"
        "- If no dialogue mentioned, use empty dialogue array\n"
        "- Always include constraints field\n\n"
        "Example:\n"
        "Input: «Старушка в ярком платке поливает цветы из старого ведра, рядом с ней стоит гигантская розовая гусеница, похожая на мягкую игрушку. Она с улыбкой говорит: \"Вот, поливаю цветочки, скоро зацветут, а ты, Гришка, не пробуй их, они для красоты!\" Гусеница вдруг издает забавный звук, и бабка чуть не расплескивает воду.»\n"
        "Output: {\n"
        '  "shot": {\n'
        '    "composition": "medium shot of elderly woman in bright headscarf watering flowers from old bucket, with giant pink caterpillar resembling soft toy standing nearby in rural yard",\n'
        '    "camera_motion": "tripod-stable, light breeze moving clothing and trees",\n'
        '    "lens": "35mm",\n'
        '    "frame_rate": "24fps",\n'
        '    "film_grain": "clean digital"\n'
        '  },\n'
        '  "environment": {\n'
        '    "location": "Exterior — rural yard with flowers",\n'
        '    "time_of_day": "afternoon",\n'
        '    "weather": "sunny, warm, clear skies, gentle breeze"\n'
        '  },\n'
        '  "characters": [\n'
        '    {\n'
        '      "name": "Elderly Woman",\n'
        '      "position": "center of frame",\n'
        '      "appearance": "elderly woman (~75-80 y.o.), bright headscarf, old bucket",\n'
        '      "action": "watering flowers, smiling"\n'
        '    },\n'
        '    {\n'
        '      "name": "Giant Pink Caterpillar",\n'
        '      "position": "next to elderly woman",\n'
        '      "appearance": "giant pink caterpillar resembling soft toy",\n'
        '      "action": "standing nearby, making funny sound"\n'
        '    }\n'
        '  ],\n'
        '  "dialogue": [\n'
        '    {\n'
        '      "character": "Elderly Woman",\n'
        '      "voice": "female (~75-80 y.o.), warm, cheerful tone",\n'
        '      "line": "Вот, поливаю цветочки, скоро зацветут, а ты, Гришка, не пробуй их, они для красоты!"\n'
        '    }\n'
        '  ],\n'
        '  "constraints": "Clear video without text or subtitles"\n'
        '}'
    )
    
    # Подготавливаем входной текст
    input_text = scene
    if replica:
        input_text += f"\nФраза: {replica}"
    
    try:
        response = gpt.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": input_text}
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        
        json_text = response.choices[0].message.content.strip()
        
        # Проверяем что это валидный JSON
        parsed_json = json.loads(json_text)
        
        # Возвращаем JSON в новом формате Veo 3
        return json.dumps(parsed_json, ensure_ascii=False)
        
    except Exception as e:
        log.error("Veo 3 JSON parser error: %s", e)
        # Fallback к старому методу
        return _rich_json_template(scene, style, replica, mode, aspect_ratio, context)

def to_json_prompt(scene: str, style: Optional[str], replica: Optional[str],
                   mode: Optional[str], aspect_ratio: str, context: Optional[str] = None) -> str:
    # если пользователь прислал уже JSON — используем как есть
    try:
        json.loads(scene)
        return scene
    except Exception:
        pass
    
    if not gpt:
        # fallback JSON если GPT недоступен
        return json.dumps({
            "model": "veo-3.0-fast",
            "duration": 8,
            "aspect_ratio": aspect_ratio,
            "style_directives": style_instructions(style),
            "shot": {"composition": "medium shot", "camera_motion": "static",
                     "lens": "35mm", "frame_rate": "24fps", "film_grain": "subtle"},
            "subject": {"description": _sanitize(scene), "voice_sync": False},
            "scene": {"location": "generic", "time_of_day": "day"},
            "action": "8s action",
            "voiceover": {"voice": "female", "line": _sanitize(replica or "")},
            "characters": [],
            "ambient": "light fx",
            "lighting": "natural",
            "mood": "neutral",
            "restrictions": "No text or logos"
        }, ensure_ascii=False)
    
    # Новый JSON-парсер для NEUROKUDO стиля
    return _neurokudo_json_parser(scene, style, replica, mode, aspect_ratio, context)

# -----------------------------------------------------------------------------
# СОСТОЯНИЕ
# -----------------------------------------------------------------------------
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        # Сначала пытаемся загрузить из базы данных
        user_data = db.get_user(uid)
        
        if user_data:
            # Пользователь найден в базе данных
            user_data["user_id"] = uid  # Добавляем user_id
            users[uid] = user_data
        else:
            # Новый пользователь - создаем структуру по умолчанию
            users[uid] = {
                "user_id": uid,  # Добавляем user_id для связи с базой данных
                "mode": None,
                "source_text": None,
                "scene": None,
                "style": None,
                "replica": None,
                "awaiting_scene": False,
                "awaiting_scene_edit": False,
                "awaiting_support": False,
                # JSON advanced
                "jsonpro": {
                    "await_text": False,
                    "last_json": None,
                    "orientation": DEFAULT_ORIENTATION,
                },
                # NKudo
                "nkudo_type": None,
                "nkudo_scene1": None,
                "nkudo_scene2": None,
                # ориентация
                "orientation": DEFAULT_ORIENTATION,
                "with_audio": DEFAULT_AUDIO,  # настройка аудио
                # монеты и биллинг
                "coins": 0,  # количество монет
                "video_bonus": 2,  # бесплатные видео для новых пользователей
                "photo_bonus": 3,  # бесплатные фото для новых пользователей
                "tryon_bonus": 1,  # бесплатная примерочная для новых пользователей
                "plan": "lite",  # тарифный план
                "jobs": {},  # история задач
                "daily": {"date": "", "videos": 0},  # дневная статистика
                "videos_left": 0,  # оставшиеся ролики
                "photos_left": 0,  # оставшиеся фотографии
                "processed_payments": set(),  # обработанные платежи для идемпотентности
                # трансформации изображений
                "awaiting_transform": False,  # ожидаем загрузку фото
                "transform_type": None,  # тип трансформации
                "transform_quality": "basic",  # качество обработки
                "transform_images": [],  # загруженные изображения
                "transform_text": None,  # текстовое описание для трансформации
                "current_job_id": None,  # ID текущей задачи
                # примерочная
                "tryon": {
                    "stage": "idle",          # idle | await_person | await_garment | confirm | after
                    "person": None,           # bytes
                    "garment": None,          # bytes
                    "dressed": None,          # bytes (последний результат VTO)
                    "await_bg": False,        # ждём фон для релокации
                    "await_prompt": False,    # ждём текст описания позы/локации
                },
            }
        
        # Сохраняем нового пользователя в базу данных
        db.save_user(uid, users[uid])

# -----------------------------------------------------------------------------
# КЛАВИАТУРЫ
# -----------------------------------------------------------------------------
def reply_main_kb():
    # Нижнее reply-меню — только SOS, кнопка «Меню» и «Не видно кнопки»
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏠 Меню")],
            [KeyboardButton("🆘 Возникли проблемы")],
            [KeyboardButton("🌓 Не видно кнопки")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_home_inline():
    # Инлайн-меню БЕЗ SOS (по просьбе)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео", callback_data="menu_make")],
        [InlineKeyboardButton("🧱LEGO мультики", callback_data="menu_lego")],
        [InlineKeyboardButton("📸 Изменить фото", callback_data="menu_transforms")],
        [InlineKeyboardButton("👗 Виртуальная примерочная", callback_data="menu_tryon")],
        [InlineKeyboardButton("🧾 JSON (для продвинутых)", callback_data="menu_jsonpro")],
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

def kb_back_only():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")]])

def kb_back_transforms():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")]])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Усложни", callback_data="var_complex"),
         InlineKeyboardButton("✂️ Упрости", callback_data="var_simple")],
        [InlineKeyboardButton("💬 Придумать фразу", callback_data="generate_replica"),
         InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_variants_with_phrase():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Усложни", callback_data="var_complex"),
         InlineKeyboardButton("✂️ Упрости", callback_data="var_simple")],
        [InlineKeyboardButton("💬 Другая фраза", callback_data="generate_replica"),
         InlineKeyboardButton("✍️ Написать фразу", callback_data="manual_replica")],
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

def kb_lego_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧱 LEGO сцена", callback_data="lego_single")],
        [InlineKeyboardButton("🎤 LEGO репортаж", callback_data="lego_reportage")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="back_modes")],
    ])

def kb_nkudo_single():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая сцена", callback_data="nkudo_regenerate_single")],
        [InlineKeyboardButton("💬 Другая фраза", callback_data="nkudo_embed_replica")],
        [InlineKeyboardButton("🧠✨ Улучшить помощником", callback_data="nkudo_improve_single")],
        [InlineKeyboardButton("➡️ Далее к стилям", callback_data="go_next")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="nkudo_menu_back")],
    ])

def kb_lego_single():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая сцена", callback_data="lego_regenerate_single")],
        [InlineKeyboardButton("💬 Другая фраза", callback_data="lego_embed_replica")],
        [InlineKeyboardButton("🧠✨ Улучшить помощником", callback_data="lego_improve_single")],
        [InlineKeyboardButton("➡️ Далее к ориентации", callback_data="go_orientation")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="lego_menu_back")],
    ])

def kb_nkudo_reportage_edit():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить сцену 1", callback_data="nkudo_reroll_scene1")],
        [InlineKeyboardButton("🎲 Крутить сцену 2", callback_data="nkudo_reroll_scene2")],
        [InlineKeyboardButton("✏️ Изменить сцену 1", callback_data="nkudo_edit_scene1")],
        [InlineKeyboardButton("✏️ Изменить сцену 2", callback_data="nkudo_edit_scene2")],
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

def kb_styles():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇯🇵 Анимэ", callback_data="style_Анимэ")],
        [InlineKeyboardButton("🧱 LEGO", callback_data="style_LEGO")],
        [InlineKeyboardButton("⏩ Без стиля – далее", callback_data="style_None")],
    ])

def kb_after_style():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать фразу", callback_data="generate_replica")],
        [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_after_replica():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="go_next")],
        [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")]
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

def kb_audio_choice():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔊 С аудио (дороже)", callback_data="audio_on")],
        [InlineKeyboardButton("🔇 Без аудио (дешевле)", callback_data="audio_off")],
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
        [InlineKeyboardButton("🔧 Доработать промт", callback_data="refine_prompt")],
        [InlineKeyboardButton("🔄 Сгенерировать ещё", callback_data="menu_make")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back_home")],
    ])

# --- Примерочная: клавиатуры ---
def kb_tryon_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
    ])

def kb_tryon_need_garment():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Сбросить", callback_data="tryon_reset")],
    ])

def kb_tryon_confirm(forward="② → ①", tryon_bonus=0):
    if tryon_bonus > 0:
        button_text = "✨ Примерить (бесплатно)"
    else:
        button_text = "✨ Примерить (−5 монеток)"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, callback_data="tryon_confirm")],
        [InlineKeyboardButton("🔁 Поменять местами", callback_data="tryon_swap")],
        [InlineKeyboardButton("❌ Сбросить", callback_data="tryon_reset")],
    ])

def kb_tryon_after():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Другая поза (новое фото человека)", callback_data="tryon_new_pose")],
        [InlineKeyboardButton("👗 Другая одежда", callback_data="tryon_new_garment")],
        [InlineKeyboardButton("🏞 Новая локация (фон фото)", callback_data="tryon_new_bg")],
        [InlineKeyboardButton("✍️ Описать позу/локацию (эксперимент)", callback_data="tryon_prompt")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back_home")],
    ])

# --- JSON (для продвинутых) ---
def kb_jsonpro_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Ввести текст сцены", callback_data="jsonpro_enter")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
    ])

def kb_jsonpro_after_text():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Вертикальное (9:16)", callback_data="jsonpro_ori_916")],
        [InlineKeyboardButton("🖥 Горизонтальное (16:9)", callback_data="jsonpro_ori_169")],
        [InlineKeyboardButton("🚀 Сгенерировать", callback_data="jsonpro_generate")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
    ])

# Новые клавиатуры для "Измени фото"
def kb_transforms():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Удалить фон (−1 монетка)", callback_data="transform_remove_bg")],
        [InlineKeyboardButton("👥 Совместить людей (−1 монетка)", callback_data="transform_merge_people")],
        [InlineKeyboardButton("🧩 Внедрить объект на фото (−1 монетка)", callback_data="transform_inject_object")],
        [InlineKeyboardButton("🪄 Магическая ретушь (−1 монетка)", callback_data="transform_retouch")],
        [InlineKeyboardButton("📷 Polaroid (−1 монетка)", callback_data="transform_polaroid")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
    ])

def kb_transform_quality():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Быстрое −1 монетка", callback_data="quality_basic")],
        [InlineKeyboardButton("🎨 Премиум −2 монетки", callback_data="quality_premium")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")],
    ])

def kb_transform_result():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Ещё вариант (−1 монетка)", callback_data="transform_retry")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")],
    ])

def kb_video_generate(with_audio=True):
    cost = 10  # COST_VIDEO
    audio_text = "🔊 Со звуком" if with_audio else "🔇 Тихий режим"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🚀 Сгенерировать ролик (−{cost} монеток)", callback_data="generate_now")],
        [InlineKeyboardButton(audio_text, callback_data="toggle_audio")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_modes")],
    ])

def kb_video_result():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Сделать ещё вариант (−10 монеток)", callback_data="video_retry")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_home")],
    ])

# -----------------------------------------------------------------------------
# ТАРИФЫ И АДДОНЫ
# -----------------------------------------------------------------------------

def pricing_text() -> str:
    return (
        "💰 Тарифы\n\n"
        "✨ *Лайт — 1 990 ₽*\n"
        "🎬 10 видео + 📸 20 фотографий\n"
        "Отлично, чтобы начать и протестировать возможности.\n\n"
        "⭐ *Стандарт — 2 490 ₽*\n"
        "🎬 16 видео + 📸 50 фотографий\n"
        "Самый удобный баланс цены и объёма.\n\n"
        "💎 *Про — 4 990 ₽*\n"
        "🎬 32 видео + 📸 120 фотографий\n"
        "Полный набор для мощного контент-плана.\n\n"
        "📸 *Фотографии* = любые фото-инструменты: виртуальная примерочная, полароид, ретушь, фон и т.д."
    )

def pricing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Купить «Лайт»", callback_data="plan:lite")],
        [InlineKeyboardButton("Купить «Стандарт»", callback_data="plan:std")],
        [InlineKeyboardButton("Купить «Про»", callback_data="plan:pro")],
        [InlineKeyboardButton("⚡ Быстрые докупки", callback_data="show_addons")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
    ])

def addons_text() -> str:
    return (
        "⚡ Быстрые докупки\n\n"
        "🎬 Видео:\n"
        "• Video 5 — 1 190 ₽ → +5 видео\n"
        "• Video 10 — 2 190 ₽ → +10 видео\n\n"
        "📸 Фото:\n"
        "• Photo 20 — 590 ₽ → +20 фотографий\n"
        "• Photo 50 — 1 190 ₽ → +50 фотографий\n\n"
        "🎛️ Микс:\n"
        "• Mix — 1 690 ₽ → +5 видео + 20 фото"
    )

def addons_keyboard(order=None) -> InlineKeyboardMarkup:
    # order — список ключей в приоритетном порядке
    keys = order or ["v5", "v10", "p20", "p50", "mix"]
    rows = [[InlineKeyboardButton(ADDONS[k]["title"], callback_data=f"addon:{k}")] for k in keys]
    rows.append([InlineKeyboardButton("← Назад к тарифам", callback_data="open:pricing")])
    return InlineKeyboardMarkup(rows)

# -----------------------------------------------------------------------------
# ДОСТУП
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# ХЭНДЛЕРЫ
# -----------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    # сброс ключевых флагов
    st = users[uid]
    st.update({
            "mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
            "awaiting_scene": False, "awaiting_custom_style": False, "awaiting_scene_edit": False,
            "awaiting_support": False, "orientation": DEFAULT_ORIENTATION, "with_audio": DEFAULT_AUDIO,
            "nkudo_type": None, "nkudo_scene1": None, "nkudo_scene2": None,
            "jsonpro": {"await_text": False, "last_json": None, "orientation": DEFAULT_ORIENTATION},
            "tryon": {"stage": "idle", "person": None, "garment": None, "dressed": None, "await_bg": False, "await_prompt": False},
            # сбрасываем только рабочие поля, монеты и план оставляем
            "awaiting_transform": False, "transform_type": None, "transform_quality": "basic",
            "transform_images": [], "transform_text": None, "current_job_id": None,
        })
    
    # Проверяем низкий баланс монет (только для существующих пользователей)
    if st.get("coins", 0) > 0 and check_low_coins(st):
        coins = st.get("coins", 0)
        videos_left = st.get("videos_left", 0)
        photos_left = st.get("photos_left", 0)
        
        await update.message.reply_text(
            f"⚠️ У вас осталось мало монет: {coins}\n\n"
            f"🎬 Видео: {videos_left}\n"
            f"📸 Фотографий: {photos_left}\n\n"
            f"💳 Пополнить баланс?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Быстрые докупки", callback_data="show_addons")],
                [InlineKeyboardButton("📚 Тарифы", callback_data="open:pricing")],
                [InlineKeyboardButton("⬅️ Пропустить", callback_data="skip_low_coins")],
            ])
        )
        return
    
    # Приветственное сообщение для новых пользователей с бонусами
    video_bonus = st.get("video_bonus", 0)
    photo_bonus = st.get("photo_bonus", 0)
    tryon_bonus = st.get("tryon_bonus", 0)
    if video_bonus > 0 or photo_bonus > 0 or tryon_bonus > 0:
        bonus_text = ""
        if video_bonus > 0:
            bonus_text += f"• {video_bonus} бесплатных видео\n"
        if photo_bonus > 0:
            bonus_text += f"• {photo_bonus} бесплатных фото-обработок\n"
        if tryon_bonus > 0:
            bonus_text += f"• {tryon_bonus} бесплатная примерочная\n"
        
        await update.message.reply_text(
            f"🎉 Добро пожаловать в Babka Bot!\n\n"
            f"🎁 Приветственные подарки:\n"
            f"{bonus_text}\n"
            f"Эти подарки расходуются в первую очередь при генерации.\n\n"
            f"Выберите функцию:",
            reply_markup=kb_home_inline()
        )
        return
    
    await update.message.reply_text("Главное меню:", reply_markup=kb_home_inline())

async def cmd_whereami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    chat = update.effective_chat
    await update.message.reply_text(
        f"chat_id: {chat.id}\n"
        f"type: {chat.type}\n"
        f"title: {getattr(chat, 'title', '')}"
    )

async def cmd_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать пользовательское соглашение"""
    terms_text = """📋 ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ
Telegram бот "Babka Bot"
Дата последнего обновления: 01.10.2025

1. ОБЩИЕ ПОЛОЖЕНИЯ
1.1. Настоящее Пользовательское соглашение (далее — «Соглашение») регулирует порядок использования сервиса генерации контента посредством Telegram бота "Babka Bot" (далее — «Сервис») и определяет взаимоотношения между Администрацией Сервиса и лицом, использующим функционал бота (далее — «Пользователь»).
1.2. Приобретая тарифный план, осуществляя оплату услуг или используя любые функции Сервиса, Пользователь безусловно принимает настоящее Соглашение в полном объёме и подтверждает, что:

• Ознакомился со всеми условиями настоящего документа
• Достиг совершеннолетия (18 лет)
• Обладает правоспособностью для заключения соглашений

1.3. В случае несогласия с любым из положений настоящего Соглашения использование Сервиса должно быть немедленно прекращено.

⚠️ СПЕЦИАЛЬНЫЕ УСЛОВИЯ И ОГРАНИЧЕНИЯ ОТВЕТСТВЕННОСТИ

3.1. Природа AI-генерируемого контента
• ВСЕ результаты генерации создаются автоматизированными алгоритмами нейронных сетей
• Администрация Сервиса выступает исключительно в роли технического агрегатора

3.2. Администрация НЕ НЕСЁТ ответственность за:
• Характеристики качества генерируемого контента
• Семантическое содержание и текстовую составляющую
• Техническую реализацию сторонних сервисов
• Соответствие ожиданиям Пользователя

4. СИСТЕМА МОНЕТИЗАЦИИ
4.1. Тарификация операций:
• Генерация видео: 10 монеток
• Обработка изображений: 1 монетка
• Первая повторная генерация: без списания

4.2. Приветственные бонусы:
• 2 бесплатные видео-генерации
• 3 бесплатные фото-обработки

4.3. Тарифные планы:
• ЛАЙТ — 1 990 ₽ (120 монеток, лимит 3 видео/день)
• СТАНДАРТ — 2 490 ₽ (200 монеток, лимит 5 видео/день)
• ПРО — 4 990 ₽ (400 монеток, лимит 10 видео/день)

4.6. Логика возвратов:
Возврат ресурсов осуществляется ТОЛЬКО при:
• Технических сбоях на стороне Сервиса
• Отсутствии файла в результате выполнения запроса
• Получении повреждённого или нечитаемого файла

Возврат НЕ осуществляется при:
• Субъективной неудовлетворённости качеством результата
• Несоответствии результата ожиданиям Пользователя
• Ошибках в составлении запроса со стороны Пользователя

9. ВОЗРАСТНЫЕ ОГРАНИЧЕНИЯ
9.1. Сервис предназначен для лиц, достигших 18 лет.

⚠️ ВАЖНОЕ НАПОМИНАНИЕ
Приобретая тариф и используя Сервис, вы подтверждаете:
• Ознакомление с условиями Соглашения
• Понимание технологической природы AI-генерации
• Принятие всех рисков, связанных с непредсказуемостью результатов
• Готовность нести полную ответственность за использование контента

Версия документа: 1.0
Дата вступления в силу: 01.10.2025"""

    await update.message.reply_text(terms_text)

async def cmd_test_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для симуляции оплаты"""
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    
    # Симулируем успешную оплату тарифа "Лайт"
    test_webhook_data = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": f"test_payment_{uid}_{int(time.time())}",
            "status": "succeeded",
            "amount": {
                "value": "1990.00",
                "currency": "RUB"
            },
            "metadata": {
                "user_id": uid,
                "plan": "lite",
                "type": "plan"
            }
        }
    }
    
    try:
        await handle_payment_webhook(test_webhook_data, context)
        await update.message.reply_text("✅ Тестовая оплата обработана успешно!")
    except Exception as e:
        log.error(f"Error in test payment: {e}")
        await update.message.reply_text(f"❌ Ошибка тестовой оплаты: {e}")

# --- Reply-кнопки (нижнее меню) как текст ---
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    # Кнопки нижнего меню
    if text == "🏠 Меню":
        await update.message.reply_text("Главное меню:", reply_markup=kb_home_inline())
        return
    if text == "🎬 Создание видео":
        await update.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if text == "🧱LEGO мультики":
        await update.message.reply_text("🧱LEGO мультики (в разработке).", reply_markup=kb_home_inline()); return
    if text == "🖼️ Оживление изображения":
        await update.message.reply_text("🖼️ Оживление изображения (в разработке).", reply_markup=kb_home_inline()); return
    if text == "👗 Виртуальная примерочная":
        st["tryon"] = {"stage": "await_person", "person": None, "garment": None, "dressed": None, "await_bg": False, "await_prompt": False}
        await update.message.reply_text(
            "👗 Виртуальная примерочная\n\n"
            "1) Пришлите фото человека, которого будем одевать\n"
            "2) Затем пришлите фото одежды (можно даже на другом человеке)",
            reply_markup=kb_tryon_start()
        ); return
    if text == "🧾 JSON (для продвинутых)":
        st["jsonpro"] = {"await_text": False, "last_json": None, "orientation": DEFAULT_ORIENTATION}
        await update.message.reply_text(
            "🧾 JSON (для продвинутых)\n"
            "Введи текст сцены, я соберу полноценный JSON-подсказчик для Veo.\n"
            "Дальше выберешь ориентацию и запустишь генерацию.",
            reply_markup=kb_jsonpro_start()
        ); return
    if text == "🆘 Возникли проблемы":
        st["awaiting_support"] = True
        await update.message.reply_text("Опиши проблему одним сообщением — перешлю её разработчику на почту."); 
        return
    if text == "🌓 Не видно кнопки":
        await update.message.reply_text(
        "Если кнопки отображаются плохо (светлый текст на светлом фоне) — "
        "поменяйте тему Telegram на ночную:\n\n"
        "⚙️ Настройки → Оформление → выберите «Тёмная тема» 🌙"
    )
        return



    # Приём репорта
    if st.get("awaiting_support"):
        st["awaiting_support"] = False
        body = f"Репорт от @{update.effective_user.username or uid} (ID {uid}):\n\n{text}"
        ok = _send_support_email("🆘 Репорт из Babka Bot", body)
        if ADMIN_CHAT_IDS:
            await notify_admins(context, f"🆘 Репорт от {uid}:\n\n{text}")
        await update.message.reply_text(
            "✅ Репорт отправлен на почту." if ok else "⚠️ Не удалось отправить на почту. Проверь SMTP.",
            reply_markup=reply_main_kb()
        )
        return

    # try-on: текстовый промт для позы/локации (экспериментальная ветка)
    if users[uid]["tryon"].get("await_prompt"):
        users[uid]["tryon"]["await_prompt"] = False
        stt = users[uid]["tryon"]
        if not stt.get("dressed"):
            await update.message.reply_text("Сначала выполните примерку, затем меняйте позу/локацию.")
            return
        prompt = text
        await update.message.reply_text("⏳ Делаю перестановку по описанию…")
        try:
            out = await asyncio.to_thread(repose_or_relocate, stt["dressed"], prompt, None)
            stt["dressed"] = out
            await update.message.reply_photo(photo=out, caption="✅ Готово (эксперимент).", reply_markup=kb_tryon_after())
        except Exception as e:
            await update.message.reply_text(f"⚠️ Не удалось переставить позу/локацию: {e}")
        return

    # Редактирование сцен (репортаж)
    if st.get("awaiting_scene_edit"):
        editing = st.get("editing_scene")
        if editing == 1: st["nkudo_scene1"] = text; await update.message.reply_text("✅ Сцена 1 обновлена!")
        elif editing == 2: st["nkudo_scene2"] = text; await update.message.reply_text("✅ Сцена 2 обновлена!")
        st["awaiting_scene_edit"] = False
        result_text = ("📮 Текущий репортаж:\n\n"
                       f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
                       f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
                       f"💬 Фраза: {st.get('replica','')}")
        await update.message.reply_text(result_text, reply_markup=kb_nkudo_reportage_edit())
        return

        
    # --- Дополнение промта текстом (умный режим через GPT) ---
    if st.get("awaiting_prompt_add"):
        st["awaiting_prompt_add"] = False
        extra = text

        # Проверяем режим репортажа
        if st.get("nkudo_type") == "reportage":
            # Для репортажа обновляем обе сцены
            base_scene1 = st.get("nkudo_scene1", "")
            base_scene2 = st.get("nkudo_scene2", "")
            
            prompt = (
                f"You are rewriting a 2-scene reportage for Veo video generation.\n\n"
                f"Scene 1: {base_scene1}\n\n"
                f"Scene 2: {base_scene2}\n\n"
                f"User asked to add: {extra}\n\n"
                f"Keep both scenes concise and cinematic.\n"
                f"Return in format:\n"
                f"SCENE1: [rewritten scene 1]\n"
                f"SCENE2: [rewritten scene 2]"
            )

            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.7,
                )
                result = resp.choices[0].message.content.strip() if resp else ""
                
                # Парсим результат
                if "SCENE1:" in result and "SCENE2:" in result:
                    parts = result.split("SCENE2:")
                    new_scene1 = parts[0].replace("SCENE1:", "").strip()
                    new_scene2 = parts[1].strip()
                else:
                    # Если формат не распознан, обновляем обе сцены одинаково
                    new_scene1 = f"{base_scene1}\n\n{extra}"
                    new_scene2 = f"{base_scene2}\n\n{extra}"
            except Exception as e:
                new_scene1 = f"{base_scene1}\n\n{extra}"
                new_scene2 = f"{base_scene2}\n\n{extra}"

            st["nkudo_scene1"] = new_scene1
            st["nkudo_scene2"] = new_scene2
            st["scene"] = f"{new_scene1}\n\n{new_scene2}"
            
            # Возвращаемся к финальному чеку
            parts = [f"✅ Сцена: {st.get('nkudo_scene1','')}\n\n{st.get('nkudo_scene2','')}"]
            # Для LEGO режима не показываем стиль, так как он автоматический
            if st.get("style") and st.get("mode") != "lego": parts.append(f"✅ Стиль: {st['style']}")
            if st.get("replica"): parts.append(f"✅ Фраза: {st['replica']}")
            if st.get("orientation"): parts.append(f"✅ Ориентация: {st['orientation']}")

            preview = "✅ Промт обновлён!\n\n" + "\n\n".join(parts)

            kb_preview = InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
                [InlineKeyboardButton("❌ Отменить процедуру", callback_data="cancel_procedure")],
                [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
            ])

            await update.message.reply_text(preview, reply_markup=kb_preview)
        else:
            # Обычный режим
            base_scene = st.get("scene", "")
            style_note = st.get("style")
            replica_note = st.get("replica")
            orientation_note = st.get("orientation")

            prompt = (
            f"You are rewriting ONLY the scene description for Veo video generation.\n\n"
            f"Base scene:\n{base_scene}\n\n"
            f"User asked to add: {extra}\n\n"
            f"Keep the scene concise and cinematic.\n"
            f"Do not change or remove Style, Replica, Orientation. "
            f"They will stay as:\n"
            f"- Style: {style_note or '—'}\n"
            f"- Replica: {replica_note or '—'}\n"
            f"- Orientation: {orientation_note or '—'}\n"
            f"Just rewrite the SCENE with the extra detail."
        )

        try:
            if not gpt:

                replica = "Да сама довезу без принцев обойдусь!"

            else:

                resp = gpt.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            new_scene = resp.choices[0].message.content.strip() if resp else base_scene
        except Exception as e:
            new_scene = f"{base_scene}\n(⚠️ Failed to regenerate scene with GPT: {e})"

        st["scene"] = new_scene

        parts = [f"✅ Сцена: {new_scene}"]
        if style_note: parts.append(f"✅ Стиль: {style_note}")
        if replica_note: parts.append(f"✅ Фраза: {replica_note}")
        if orientation_note: parts.append(f"✅ Ориентация: {orientation_note}")

        preview = "✅ Промт обновлён!\n\n" + "\n\n".join(parts)

        await update.message.reply_text(
            preview,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
                [InlineKeyboardButton("❌ Отменить процедуру", callback_data="cancel_procedure")],
                [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
            ])
        )
        return

    # --- Ручной ввод фрази ---
    if st.get("awaiting_manual_replica"):
        st["awaiting_manual_replica"] = False
        
        # Обрабатываем ввод фразы через GPT для адаптации
        if "говорит" in text.lower() or "восклицает" in text.lower() or "шепчет" in text.lower():
            # Если пользователь написал "Бабка говорит «фраза»", извлекаем только фразу
            extract_prompt = (
                f"Извлеки только фразу из текста, убрав слова автора.\n\n"
                f"Текст: {text}\n\n"
                f"ТРЕБОВАНИЯ:\n"
                f"- Верни только саму фразу в кавычках\n"
                f"- Убери слова типа 'говорит', 'восклицает', 'шепчет' и т.д.\n"
                f"- Сохрани только содержание речи\n\n"
                f"Пример: 'Бабка говорит «Привет»' → 'Привет'\n"
                f"Пример: 'Она восклицает «Ну нихера себе!»' → 'Ну нихера себе!'\n\n"
                f"Верни только фразу без дополнительных комментариев."
            )
            
            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": extract_prompt}],
                    max_tokens=50,
                    temperature=0.3,
                )
                extracted_phrase = resp.choices[0].message.content.strip() if resp else ""
                # Убираем кавычки, если они есть
                if extracted_phrase.startswith('"') and extracted_phrase.endswith('"'):
                    extracted_phrase = extracted_phrase[1:-1]
                elif extracted_phrase.startswith('«') and extracted_phrase.endswith('»'):
                    extracted_phrase = extracted_phrase[1:-1]
                st["replica"] = _clean_replica(extracted_phrase)
            except Exception as e:
                # Если не удалось обработать через GPT, используем исходный текст
                st["replica"] = _clean_replica(text)
        else:
            # Обычная обработка
            st["replica"] = _clean_replica(text)  # Очищаем от тире
        
        if st.get("from_final_check"):
            # Возвращаемся к финальному чеку
            st["from_final_check"] = False
            parts = [f"✅ Сцена: {st.get('scene','')}"]
            # Для LEGO режима не показываем стиль, так как он автоматический
            if st.get("style") and st.get("mode") != "lego": parts.append(f"✅ Стиль: {st['style']}")
            if st.get("replica"): parts.append(f"✅ Фраза: {st['replica']}")
            if st.get("orientation"): parts.append(f"✅ Ориентация: {st['orientation']}")

            preview = "📝 Итоговый промт для генерации:\n\n" + "\n\n".join(parts)

            kb_preview = InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
                [InlineKeyboardButton("❌ Отменить процедуру", callback_data="cancel_procedure")],
                [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
            ])

            await update.message.reply_text(preview, reply_markup=kb_preview)
        else:
            # Обычное меню фрази
            if st.get("mode") == "nkudo":
                # Для режима NEUROKUDO показываем обычное меню
                await update.message.reply_text(
                    f"✅ Фраза обновлена: {st['replica']}\n\nТеперь можно изменить или продолжить:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
                        [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")]
                    ])
                )
            else:
                # Для обычного режима встраиваем фразу в сцену
                if st.get("scene"):
                    # Встраиваем фразу в сцену через GPT
                    embed_prompt = (
                        f"Встрой фразу в описание сцены как речь персонажа.\n\n"
                        f"Исходная сцена: {st['scene']}\n"
                        f"Фраза: {st['replica']}\n\n"
                        f"ТРЕБОВАНИЯ:\n"
                        f"- Встрой фразу как прямую речь персонажа в кавычках\n"
                        f"- Добавь слова автора типа 'говорит', 'восклицает', 'шепчет' и т.д.\n"
                        f"- Фраза должна звучать естественно в контексте сцены\n"
                        f"- Сцена должна остаться целостной и логичной\n\n"
                        f"Верни только обновленное описание сцены без дополнительных комментариев."
                    )
                    
                    try:
                        if not gpt:

                            replica = "Да сама довезу без принцев обойдусь!"

                        else:

                            resp = gpt.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=[{"role": "user", "content": embed_prompt}],
                            max_tokens=200,
                            temperature=0.7,
                        )
                        updated_scene = resp.choices[0].message.content.strip() if resp else base_scene
                        st["scene"] = updated_scene
                    except Exception as e:
                        updated_scene = f"{st['scene']}\n\nБабушка говорит: {st['replica']}"
                        st["scene"] = updated_scene
                    
                    txt = f"💬 Фраза встроена в сцену\n\n🎬 Обновленная сцена:\n{st['scene']}\n\nЧто делаем дальше?"
                    await update.message.reply_text(txt, reply_markup=kb_variants_with_phrase())
                else:
                    await update.message.reply_text(
                        f"✅ Фраза обновлена: {st['replica']}\n\nТеперь можно изменить или продолжить:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
                            [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")]
                        ])
                    )
        return

    # --- Доработка промта ---
    if st.get("awaiting_prompt_refine"):
        st["awaiting_prompt_refine"] = False
        refinement = text
        
        base_scene = st.get("scene", "")
        style_note = st.get("style")
        replica_note = st.get("replica")
        orientation_note = st.get("orientation")

        prompt = (
            f"You are improving a video generation prompt based on user feedback.\n\n"
            f"Current scene: {base_scene}\n"
            f"Current style: {style_note or '—'}\n"
            f"Current replica: {replica_note or '—'}\n"
            f"Current orientation: {orientation_note or '—'}\n\n"
            f"User wants to change/add: {refinement}\n\n"
            f"Please improve the SCENE description based on the user's request. "
            f"Keep the scene concise and cinematic. "
            f"Do not change Style, Replica, or Orientation unless specifically requested. "
            f"Return only the improved scene description."
        )

        try:
            if not gpt:

                replica = "Да сама довезу без принцев обойдусь!"

            else:

                resp = gpt.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            new_scene = resp.choices[0].message.content.strip() if resp else base_scene
        except Exception as e:
            new_scene = f"{base_scene}\n(⚠️ Failed to refine scene with GPT: {e})"

        st["scene"] = new_scene

        parts = [f"✅ Сцена: {new_scene}"]
        if style_note: parts.append(f"✅ Стиль: {style_note}")
        if replica_note: parts.append(f"✅ Фраза: {replica_note}")
        if orientation_note: parts.append(f"✅ Ориентация: {orientation_note}")

        preview = "✅ Промт доработан!\n\n" + "\n\n".join(parts)

        await update.message.reply_text(
            preview,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
                [InlineKeyboardButton("❌ Отменить процедуру", callback_data="cancel_procedure")],
                [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
            ])
        )
        return

    # Ожидание сцены (manual/helper)
    if st.get("awaiting_scene"):
        st["awaiting_scene"] = False; st["source_text"] = text
        if st["mode"] == "helper" and gpt:
            try:
                log.info(f"Helper mode: processing text '{text[:50]}...'")
                scene = improve_scene(text, mode="normal")
                if scene and scene.strip():
                    st["scene"] = scene
                    log.info(f"Helper mode: scene improved successfully")
                    await update.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{scene}", reply_markup=kb_variants())
                    return
                else:
                    # Если помощник не смог улучшить, используем исходный текст
                    log.warning(f"Helper mode: improve_scene returned empty result")
                    st["scene"] = text
                    await update.message.reply_text(f"📝 Промт принят (помощник недоступен):\n\n{text}", reply_markup=kb_variants())
                    return
            except Exception as e:
                log.error(f"Error in improve_scene: {e}")
                # В случае ошибки используем исходный текст
                st["scene"] = text
                await update.message.reply_text(f"📝 Промт принят (ошибка помощника):\n\n{text}", reply_markup=kb_variants())
                return
        elif st["mode"] == "helper" and not gpt:
            log.warning("Helper mode: gpt not initialized")
            st["scene"] = text
            await update.message.reply_text(f"📝 Промт принят (GPT недоступен - используется исходный текст):\n\n{text}", reply_markup=kb_variants())
            return
        st["scene"] = text
        await update.message.reply_text(f"📝 Промт принят:\n\n{text}", reply_markup=kb_variants())
        return
    

    # --- Обработка ожидания текста для трансформаций ---
    if st.get("awaiting_transform", False):
        transform_type = st.get("transform_type")
        
        if transform_type in ("inject_object", "retouch"):
            st["transform_text"] = text
            st["awaiting_transform"] = False
            
            if transform_type == "inject_object":
                await update.message.reply_text(
                    f"✅ Описание объекта принято!\n\n"
                    f"Объект: {text}\n\n"
                    f"Теперь пришлите фото, куда добавить объект."
                )
            else:  # retouch
                await update.message.reply_text(
                    f"✅ Описание ретуши принято!\n\n"
                    f"Ретушь: {text}\n\n"
                    f"Теперь пришлите фото для обработки."
                )
            
            # Включаем режим ожидания фото
            st["awaiting_transform"] = True
            return

    # JSON PRO: ожидание текста сцены
    if st["jsonpro"].get("await_text"):
        st["jsonpro"]["await_text"] = False
        # генерим JSON без показа в обычных режимах — здесь наоборот ПОКАЗЫВАЕМ, это раздел для продвинутых
        jj = to_json_prompt(text, style=None, replica=None, mode="manual",
                            aspect_ratio=st["jsonpro"].get("orientation", DEFAULT_ORIENTATION), context=None)
        st["jsonpro"]["last_json"] = jj
        await update.message.reply_text("🧾 JSON:\n```\n" + jj + "\n```", parse_mode="Markdown",
                                        reply_markup=kb_jsonpro_after_text())
        return

    # по умолчанию
    await update.message.reply_text("Главное меню:", reply_markup=kb_home_inline())

# --- Webhook обработчик для ЮKassa ---
async def handle_payment_webhook(webhook_data: dict, context: ContextTypes.DEFAULT_TYPE):
    """Обработать webhook от ЮKassa"""
    try:
        payment_info = process_payment_webhook(webhook_data)
        if not payment_info:
            log.warning("Invalid webhook data received")
            return
        
        user_id = payment_info.get("user_id")
        payment_id = payment_info.get("payment_id")
        amount = payment_info.get("amount")
        metadata = payment_info.get("metadata", {})
        
        if not user_id:
            log.warning("No user_id in payment metadata")
            return
        
        # Проверяем идемпотентность
        if not _ensure(user_id):
            log.error(f"Failed to ensure user {user_id}")
            return
            
        st = users[user_id]
        
        # Проверяем, не обрабатывали ли уже этот платеж
        processed_payments = st.get("processed_payments", set())
        if payment_id in processed_payments:
            log.info(f"Payment {payment_id} already processed for user {user_id}")
            return
        
        # Добавляем в обработанные
        processed_payments.add(payment_id)
        st["processed_payments"] = processed_payments
        
        # Обрабатываем в зависимости от типа
        if "plan" in metadata:
            plan_key = metadata["plan"]
            plan = PLANS[plan_key]
            
            # Добавляем монетки и квоты
            st["coins"] = st.get("coins", 0) + plan["coins"]
            st["videos_left"] = st.get("videos_left", 0) + plan["videos"]
            st["photos_left"] = st.get("photos_left", 0) + plan["photos"]
            st["plan"] = plan_key
            
            message = (
                f"✅ Оплата получена!\n\n"
                f"📋 Тариф {plan['name']} активирован:\n"
                f"• +{plan['coins']} монеток\n"
                f"• +{plan['videos']} видео\n"
                f"• +{plan['photos']} фотографий\n\n"
                f"💰 Текущий баланс:\n"
                f"• {st['coins']} монеток\n"
                f"• {st['videos_left']} видео\n"
                f"• {st['photos_left']} фотографий"
            )
            
        elif "addon" in metadata:
            addon_key = metadata["addon"]
            addon = ADDONS[addon_key]
            
            # Добавляем монетки и квоты
            st["coins"] = st.get("coins", 0) + addon["coins"]
            st["videos_left"] = st.get("videos_left", 0) + addon["videos"]
            st["photos_left"] = st.get("photos_left", 0) + addon["photos"]
            
            description = []
            if addon["videos"] > 0:
                description.append(f"• +{addon['videos']} видео")
            if addon["photos"] > 0:
                description.append(f"• +{addon['photos']} фотографий")
            
            message = (
                f"✅ Оплата получена!\n\n"
                f"📋 {addon['title']} активирован:\n"
                + "\n".join(description) + f"\n"
                f"• +{addon['coins']} монеток\n\n"
                f"💰 Текущий баланс:\n"
                f"• {st['coins']} монеток\n"
                f"• {st['videos_left']} видео\n"
                f"• {st['photos_left']} фотографий"
            )
        else:
            log.warning(f"Unknown payment type in metadata: {metadata}")
            return
        
        # Отправляем уведомление пользователю
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
                    [InlineKeyboardButton("📚 Тарифы", callback_data="open:pricing")],
                ])
            )
        except Exception as e:
            log.error(f"Failed to send payment notification to user {user_id}: {e}")
        
        log.info(f"Payment {payment_id} processed successfully for user {user_id}")
        
    except Exception as e:
        log.error(f"Error processing payment webhook: {e}")

# --- Приём фото (для примерочной и т.п.) ---
async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]

    # --- Обработка фото для трансформаций ---
    if st.get("awaiting_transform", False):
        transform_type = st.get("transform_type")
        
        # Скачиваем фото
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            b = await file.download_as_bytearray()
            photo_bytes = bytes(b)
        except Exception as e:
            log.error("Failed to download photo: %s", e)
            await update.message.reply_text("❌ Ошибка загрузки фото. Попробуйте ещё раз.")
            return
        
        # Добавляем фото в список
        if "transform_images" not in st:
            st["transform_images"] = []
        st["transform_images"].append(photo_bytes)
        
        # Проверяем, достаточно ли фото
        required_photos = 1
        if transform_type == "merge_people":
            required_photos = 2  # минимум 2 человека
        elif transform_type == "polaroid":
            required_photos = 1  # минимум 1 фото
        
        if len(st["transform_images"]) < required_photos:
            remaining = required_photos - len(st["transform_images"])
            await update.message.reply_text(
                f"✅ Фото {len(st['transform_images'])}/{required_photos} получено.\n\n"
                f"Пришлите ещё {remaining} фото."
            )
            return
        
        # Все фото получены, начинаем обработку
        try:
            # Проверяем монеты
            quality = st.get("transform_quality", "basic")
            cost = 1 if quality == "basic" else 2
            
            if not can_generate_photo(st, cost):
                photo_bonus = st.get("photo_bonus", 0)
                coins = st.get("coins", 0)
                
                await update.message.reply_text(
                    f"❌ Не хватает ресурсов для обработки фото.\n\n"
                    f"🎁 Бонусных фото: {photo_bonus}\n"
                    f"💰 Монеток: {coins} (нужно: {cost})\n\n"
                    f"💳 Докупить монеты?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Докупить", callback_data="buy_coins_20")],
                        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")],
                    ])
                )
                return
            
            # Создаем задачу
            job_id = hold_and_start(st, "transform", quality)
            st["current_job_id"] = job_id
            
            # Отправляем в обработку
            await update.message.reply_text(
                f"🔄 Обрабатываю фото...\n"
                f"💰 Списано: {cost} монетка\n"
                f"⏱️ Это может занять 1-2 минуты."
            )
            
            # Обрабатываем трансформацию
            result_bytes = await asyncio.to_thread(
                process_transform, 
                transform_type, 
                st["transform_images"], 
                st.get("transform_text"), 
                quality
            )
            
            # Отмечаем успех
            on_success(st, job_id)
            
            # Отправляем результат
            caption = f"✅ {transform_type.replace('_', ' ').title()} готово!"
            if transform_type == "polaroid":
                caption = "✅ Polaroid готов!"
            
            await update.message.reply_photo(
                photo=result_bytes,
                caption=caption,
                reply_markup=kb_transform_result()
            )
            
            # Очищаем состояние
            st["awaiting_transform"] = False
            st["transform_images"] = []
            st["transform_text"] = None
            
        except Exception as e:
            log.error("Transform processing error: %s", e)
            if st.get("current_job_id"):
                on_error(st, st["current_job_id"])
            await update.message.reply_text(
                f"❌ Ошибка обработки: {str(e)}\n\n"
                f"Монетки возвращены. Попробуйте ещё раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="transform_retry")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")],
                ])
            )
        return

    # --- Обработка фото для примерочной ---
    stt = st["tryon"]
    if stt["stage"] not in ("await_person", "await_garment", "confirm") and not stt.get("await_bg"):
        await update.message.reply_text(
            "Фото получено. Для виртуальной примерочной — зайдите в 👗 Виртуальная примерочная.",
            reply_markup=kb_home_inline()
        )
        return

    # скачать bytes
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        b = await file.download_as_bytearray()
        b = bytes(b)
    except Exception as e:
        await update.message.reply_text("Не смог скачать фото. Пришлите как изображение (не как файл).")
        return

    # ждём фон (перелокация)
    if stt.get("await_bg"):
        stt["await_bg"] = False
        bg_bytes = b
        if not stt.get("dressed"):
            await update.message.reply_text("Сначала выполните примерку, затем меняйте локацию.")
            return
        await update.message.reply_text("⏳ Пересобираю с новым фоном…")
        try:
            out = await asyncio.to_thread(repose_or_relocate, stt["dressed"], "", bg_bytes)
            stt["dressed"] = out
            await update.message.reply_photo(photo=out, caption="✅ Новая локация готова.", reply_markup=kb_tryon_after())
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка при смене локации: {e}")
        return

    # обычный флоу: человек/одежда
    if stt["stage"] == "await_person":
        stt["person"] = b
        stt["stage"] = "await_garment"
        await update.message.reply_text("✅ Фото человека получено.\nТеперь пришлите фото одежды.",
                                        reply_markup=kb_tryon_need_garment())
        return

    if stt["stage"] == "await_garment":
        stt["garment"] = b
        stt["stage"] = "confirm"
        await update.message.reply_text(
            "Фото получены. Готовы примерять?",
            reply_markup=kb_tryon_confirm("② → ①", st.get("tryon_bonus", 0))
        )
        return

    if stt["stage"] == "confirm":
        await update.message.reply_text("У нас уже есть оба снимка. Нажмите «✨ Примерить» или «🔁 Поменять местами».",
                                        reply_markup=kb_tryon_confirm("② → ①", st.get("tryon_bonus", 0)))

# --- Инлайн кнопки ---
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; _ensure(uid); st = users[uid]; data = q.data
    log.info("Button: %s", data)

    # Главные пункты
    if data == "menu_make":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_lego":
        # Активируем LEGO режим
        st.update({"mode": "lego", "scene": None, "style": "LEGO", "replica": None})
        await q.message.edit_text("🧱 Режим «LEGO мультики» активирован!")
        explanation = ("🧱 Режим для создания LEGO мультиков: генерируем сцены в стиле LEGO с автоматическим стилем!\n\nВыберите тип сюжета:")
        await q.message.reply_text(explanation, reply_markup=kb_lego_menu()); return
    if data == "menu_alive":
        await q.message.edit_text("🖼️ Оживление изображения (в разработке)."); return
    if data == "menu_tryon":
        st["tryon"] = {"stage": "await_person", "person": None, "garment": None, "dressed": None, "await_bg": False, "await_prompt": False}
        await q.message.edit_text(
            "👗 Виртуальная примерочная\n\n"
            "1) Пришлите фото человека, которого будем одевать\n"
            "2) Затем пришлите фото одежды (можно даже на другом человеке)",
            reply_markup=kb_tryon_start()
        ); return
    # --- Обработка пропуска предупреждения о низком балансе ---
    if data == "skip_low_coins":
        await q.message.edit_text(
            "🏠 Главное меню",
            reply_markup=kb_home_inline()
        )
        return

    # --- Трансформации изображений ---
    if data == "menu_transforms":
        coins = st.get("coins", 0)
        await q.message.edit_text(
            f"📸 Изменить фото\n\n"
            f"💰 У тебя: {coins} монеток\n\n"
            f"✨ Удалить фон (−1 монетка)\n"
            f"Вырежу фон. Могу поставить белый/градиент/ваш фон.\n\n"
            f"👥 Совместить людей (−1 монетка)\n"
            f"Соберу всех в один кадр, как будто снимались вместе.\n\n"
            f"🧩 Внедрить объект на фото (−1 монетка)\n"
            f"Добавлю предмет и впишу по свету/перспективе.\n\n"
            f"🪄 Магическая ретушь (−1 монетка)\n"
            f"Уберу лишнее или добавлю деталь. Можно указать область.\n\n"
            f"📷 Polaroid (−1 монетка)\n"
            f"Рамка, плёночное зерно, подпись.",
            reply_markup=kb_transforms()
        )
        return

    # --- Обработчики трансформаций ---
    if data == "transform_remove_bg":
        st["transform_type"] = "remove_bg"
        await q.message.edit_text(
            "✨ Удалить фон\n\n"
            "Выберите качество обработки:",
            reply_markup=kb_transform_quality()
        )
        return

    if data == "transform_merge_people":
        st["transform_type"] = "merge_people"
        await q.message.edit_text(
            "👥 Совместить людей\n\n"
            "Пришлите 2-3 фото людей (по одному фото на человека).\n"
            "Выберите качество обработки:",
            reply_markup=kb_transform_quality()
        )
        return

    if data == "transform_inject_object":
        st["transform_type"] = "inject_object"
        await q.message.edit_text(
            "🧩 Внедрить объект на фото\n\n"
            "Выберите качество обработки:",
            reply_markup=kb_transform_quality()
        )
        return

    if data == "transform_retouch":
        st["transform_type"] = "retouch"
        await q.message.edit_text(
            "🪄 Магическая ретушь\n\n"
            "Пришлите фото для ретуши.\n"
            "Выберите качество обработки:",
            reply_markup=kb_transform_quality()
        )
        return

    if data == "transform_polaroid":
        st["transform_type"] = "polaroid"
        await q.message.edit_text(
            "📷 Polaroid\n\n"
            "Пришлите 1-4 фото людей для создания Polaroid.\n"
            "Выберите качество обработки:",
            reply_markup=kb_transform_quality()
        )
        return

    # --- Выбор качества ---
    if data in ("quality_basic", "quality_premium"):
        st["transform_quality"] = "basic" if data == "quality_basic" else "premium"
        transform_type = st.get("transform_type")
        
        if transform_type == "remove_bg":
            text = "✨ Удалить фон\n\nПришлите фото для удаления фона."
        elif transform_type == "merge_people":
            text = "👥 Совместить людей\n\nПришлите 2-3 фото людей (по одному на человека)."
        elif transform_type == "inject_object":
            text = "🧩 Внедрить объект на фото\n\nОпишите объект, который нужно добавить (например: 'красная чашка кофе'):"
            st["awaiting_transform"] = True
            await q.message.edit_text(text)
            return
        elif transform_type == "retouch":
            text = "🪄 Магическая ретушь\n\nОпишите что убрать или добавить (например: 'убери прохожего слева'):"
            st["awaiting_transform"] = True
            await q.message.edit_text(text)
            return
        elif transform_type == "polaroid":
            text = "📷 Polaroid\n\nПришлите 1-4 фото людей для создания Polaroid."
        else:
            text = "Пришлите фото для обработки."
        
        quality_text = "⚡ Быстрое" if st["transform_quality"] == "basic" else "🎨 Премиум"
        cost = 1 if st["transform_quality"] == "basic" else 2
        
        await q.message.edit_text(
            f"{text}\n\n"
            f"✅ Качество: {quality_text}\n"
            f"💰 Стоимость: {cost} монетки",
            reply_markup=kb_back_transforms()
        )
        st["awaiting_transform"] = True
        return

    if data == "menu_jsonpro":
        st["jsonpro"] = {"await_text": False, "last_json": None, "orientation": DEFAULT_ORIENTATION}
        await q.message.edit_text(
            "🧾 JSON (для продвинутых)\n"
            "Введи текст сцены, я соберу полноценный JSON-подсказчик для Veo.\n"
            "Дальше выберешь ориентацию и запустишь генерацию.",
            reply_markup=kb_jsonpro_start()
        ); return
    if data == "menu_guides":
        await q.message.edit_text(pricing_text(), reply_markup=pricing_keyboard())
        return
    if data == "menu_profile":
        coins = st.get("coins", 0)
        video_bonus = st.get("video_bonus", 0)
        photo_bonus = st.get("photo_bonus", 0)
        tryon_bonus = st.get("tryon_bonus", 0)
        plan = st.get("plan", "lite")
        plan_name = PLANS.get(plan, {}).get("name", "Не выбран")
        videos_left = st.get("videos_left", 0)
        photos_left = st.get("photos_left", 0)
        
        profile_text = f"👤 Профиль\n\n"
        
        if video_bonus > 0 or photo_bonus > 0 or tryon_bonus > 0:
            bonus_items = []
            if video_bonus > 0:
                bonus_items.append(f"{video_bonus} видео")
            if photo_bonus > 0:
                bonus_items.append(f"{photo_bonus} фото")
            if tryon_bonus > 0:
                bonus_items.append(f"{tryon_bonus} примерочная")
            profile_text += f"🎁 Подарки: {', '.join(bonus_items)}\n"
        
        profile_text += f"💰 Монетки: {coins}\n"
        profile_text += f"📊 Тариф: {plan_name}\n"
        profile_text += f"🎬 Видео: {videos_left}\n"
        profile_text += f"📸 Фотографий: {photos_left}\n\n"
        profile_text += f"💡 Пример: видео = 10 монеток, преобразование = 1 монетка"
        
        await q.message.edit_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Быстрые докупки", callback_data="show_addons")],
                [InlineKeyboardButton("📚 Тарифы", callback_data="open:pricing")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
            ])
        )
        return

    # --- Покупка монет ---
    if data == "buy_coins":
        buttons = []
        for top_up in TOP_UPS:
            label = f"+{top_up['coins']} монеток — {top_up['price_rub']} ₽"
            if top_up.get("label"):
                label += f" ({top_up['label']})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"buy_{top_up['coins']}")])
        
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_profile")])
        
        await q.message.edit_text(
            "💳 Докупить монетки\n\n"
            "Выберите количество монеток для покупки:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # --- Обработка конкретной покупки ---
    if data.startswith("buy_"):
        coins_to_buy = int(data.split("_")[1])
        top_up = next((t for t in TOP_UPS if t["coins"] == coins_to_buy), None)
        
        if top_up:
            await q.message.edit_text(
                f"💳 Покупка {coins_to_buy} монеток за {top_up['price_rub']} ₽\n\n"
                f"Функция оплаты будет добавлена позже.\n"
                f"Пока что монетки можно получить через тарифные планы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Тарифные планы", callback_data="change_plan")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="buy_coins")],
                ])
            )
        return

    # --- Смена тарифа ---
    if data == "change_plan":
        buttons = []
        for plan_id, plan_data in PLANS.items():
            label = f"{plan_data['name']} — {plan_data['price_rub']} ₽ • {plan_data['coins']} монеток"
            if plan_data.get("recommended"):
                label += " (Рекомендуем)"
            buttons.append([InlineKeyboardButton(label, callback_data=f"plan_{plan_id}")])
        
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_guides")])
        
        await q.message.edit_text(
            "📊 Тарифные планы\n\n"
            "Выберите подходящий тариф:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # --- Обработка выбора тарифа ---
    if data.startswith("plan_"):
        plan_id = data.split("_")[1]
        if plan_id in PLANS:
            plan_data = PLANS[plan_id]
            await q.message.edit_text(
                f"📊 Тариф {plan_data['name']}\n\n"
                f"💰 Цена: {plan_data['price_rub']} ₽\n"
                f"🪙 Монеты: {plan_data['coins']}\n"
                f"🎬 Видео в день: {DAILY_CAP_VIDEOS.get(plan_id, 3)}\n\n"
                f"Функция смены тарифа будет добавлена позже.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="change_plan")],
                ])
            )
        return

    # --- Ретраи ---
    if data == "video_retry":
        if not st.get("current_job_id"):
            await q.message.reply_text("❌ Нет активной задачи для ретрая.")
            return
        
        job_id = st["current_job_id"]
        if not can_retry(st, job_id):
            retry_cost = get_retry_cost(st, job_id)
            await q.message.reply_text(
                f"❌ Не хватает монет для ретрая.\n"
                f"Нужно: {retry_cost} монет, у вас: {st.get('coins', 0)} монет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Докупить монеты", callback_data="buy_coins")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
                ])
            )
            return
        
        # Делаем ретрай
        if retry(st, job_id):
            await q.message.edit_text(
                "🔄 Создаю ещё вариант видео...\n"
                f"💰 {'Списано: ' + str(get_retry_cost(st, job_id)) + ' монет' if get_retry_cost(st, job_id) > 0 else 'Бесплатный ретрай'}"
            )
            # Здесь будет повторная генерация видео
            # Пока заглушка
            await asyncio.sleep(3)
            await q.message.edit_text("✅ Новый вариант готов!", reply_markup=kb_video_result())
        return

    if data == "transform_retry":
        if not st.get("current_job_id"):
            await q.message.reply_text("❌ Нет активной задачи для ретрая.")
            return
        
        job_id = st["current_job_id"]
        if not can_retry(st, job_id):
            retry_cost = get_retry_cost(st, job_id)
            await q.message.reply_text(
                f"❌ Не хватает монет для ретрая.\n"
                f"Нужно: {retry_cost} монет, у вас: {st.get('coins', 0)} монет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Докупить монеты", callback_data="buy_coins")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_transforms")],
                ])
            )
            return
        
        # Делаем ретрай
        if retry(st, job_id):
            await q.message.edit_text(
                "🔄 Обрабатываю фото ещё раз...\n"
                f"💰 {'Списано: ' + str(get_retry_cost(st, job_id)) + ' монет' if get_retry_cost(st, job_id) > 0 else 'Бесплатный ретрай'}"
            )
            # Повторная обработка фото
            transform_type = st.get("transform_type")
            quality = st.get("transform_quality", "basic")
            
            result_bytes = await asyncio.to_thread(
                process_transform, 
                transform_type, 
                st["transform_images"], 
                st.get("transform_text"), 
                quality
            )
            
            # Отмечаем успех
            on_success(st, job_id)
            
            # Отправляем результат
            caption = f"✅ Новый вариант готов!"
            if transform_type == "polaroid":
                caption = "✅ Новый Polaroid готов!"
            
            await q.message.reply_photo(
                photo=result_bytes,
                caption=caption,
                reply_markup=kb_transform_result()
            )
        return

    # -----------------------------------------------------------------------------
    # ТАРИФЫ И АДДОНЫ
    # -----------------------------------------------------------------------------
    
    # Покупка тарифа
    if data.startswith("plan:"):
        plan_key = data.split(":")[1]
        plan = PLANS[plan_key]
        
        try:
            payment_url = create_payment_link(
                user_id=q.from_user.id,
                amount=plan["price_rub"],
                description=f"Тариф {plan['name']} - {plan['videos']} видео + {plan['photos']} фото",
                metadata={"plan": plan_key, "type": "plan"}
            )
            
            await q.edit_message_text(
                f"Выбрано: {plan['name']} — {plan['price_rub']} ₽\n"
                f"После оплаты лимиты будут зачислены автоматически.\n\n"
                f"📋 Что включено:\n"
                f"• {plan['videos']} видео\n"
                f"• {plan['photos']} фотографий\n\n"
                f"📋 Соглашаясь на оплату, вы принимаете условия оферты:\n"
                f"/terms — Пользовательское соглашение",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
                    [InlineKeyboardButton("📋 Оферта", callback_data="show_terms")],
                    [InlineKeyboardButton("← Назад к тарифам", callback_data="open:pricing")],
                ])
            )
        except Exception as e:
            log.error(f"Error creating payment for plan {plan_key}: {e}")
            await q.edit_message_text(
                "❌ Ошибка создания платежа. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← Назад", callback_data="open:pricing")],
                ])
            )
        return
    
    # Покупка аддона
    if data.startswith("addon:"):
        addon_key = data.split(":")[1]
        addon = ADDONS[addon_key]
        
        try:
            payment_url = create_payment_link(
                user_id=q.from_user.id,
                amount=addon["price_rub"],
                description=addon["title"],
                metadata={"addon": addon_key, "type": "addon"}
            )
            
            description = f"• {addon['videos']} видео" if addon['videos'] > 0 else ""
            if addon['photos'] > 0:
                description += f"\n• {addon['photos']} фотографий" if addon['videos'] > 0 else f"• {addon['photos']} фотографий"
            
            await q.edit_message_text(
                f"Выбрано: {addon['title']}\n"
                f"После оплаты лимиты будут зачислены автоматически.\n\n"
                f"📋 Что включено:\n{description}\n\n"
                f"📋 Соглашаясь на оплату, вы принимаете условия оферты:\n"
                f"/terms — Пользовательское соглашение",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
                    [InlineKeyboardButton("📋 Оферта", callback_data="show_terms")],
                    [InlineKeyboardButton("← Назад", callback_data="show_addons")],
                ])
            )
        except Exception as e:
            log.error(f"Error creating payment for addon {addon_key}: {e}")
            await q.edit_message_text(
                "❌ Ошибка создания платежа. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← Назад", callback_data="show_addons")],
                ])
            )
        return
    
    # Показать аддоны
    if data == "show_addons":
        # Контекстная расстановка приоритета
        uid = q.from_user.id
        st = users.get(uid, {})
        videos_left = st.get("videos_left", 0)
        photos_left = st.get("photos_left", 0)
        
        order = []
        if videos_left <= 2:
            order += ["v5", "v10"]
        if photos_left <= 10:
            order += ["p20", "p50"]
        # добиваем до полного списка, сохраняя уникальность
        for k in ["v5", "v10", "p20", "p50", "mix"]:
            if k not in order: 
                order.append(k)
        
        await q.edit_message_text(addons_text(), reply_markup=addons_keyboard(order))
        return
    
    # Навигация
    if data == "open:pricing":
        await q.edit_message_text(pricing_text(), reply_markup=pricing_keyboard())
        return
    
    # Показать оферту
    if data == "show_terms":
        terms_text = """📋 ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ
Telegram бот "Babka Bot"
Дата последнего обновления: 01.10.2025

1. ОБЩИЕ ПОЛОЖЕНИЯ
1.1. Настоящее Пользовательское соглашение (далее — «Соглашение») регулирует порядок использования сервиса генерации контента посредством Telegram бота "Babka Bot" (далее — «Сервис») и определяет взаимоотношения между Администрацией Сервиса и лицом, использующим функционал бота (далее — «Пользователь»).
1.2. Приобретая тарифный план, осуществляя оплату услуг или используя любые функции Сервиса, Пользователь безусловно принимает настоящее Соглашение в полном объёме и подтверждает, что:

• Ознакомился со всеми условиями настоящего документа
• Достиг совершеннолетия (18 лет)
• Обладает правоспособностью для заключения соглашений

1.3. В случае несогласия с любым из положений настоящего Соглашения использование Сервиса должно быть немедленно прекращено.

⚠️ СПЕЦИАЛЬНЫЕ УСЛОВИЯ И ОГРАНИЧЕНИЯ ОТВЕТСТВЕННОСТИ

3.1. Природа AI-генерируемого контента
• ВСЕ результаты генерации создаются автоматизированными алгоритмами нейронных сетей
• Администрация Сервиса выступает исключительно в роли технического агрегатора

3.2. Администрация НЕ НЕСЁТ ответственность за:
• Характеристики качества генерируемого контента
• Семантическое содержание и текстовую составляющую
• Техническую реализацию сторонних сервисов
• Соответствие ожиданиям Пользователя

4. СИСТЕМА МОНЕТИЗАЦИИ
4.1. Тарификация операций:
• Генерация видео: 10 монеток
• Обработка изображений: 1 монетка
• Первая повторная генерация: без списания

4.2. Приветственные бонусы:
• 2 бесплатные видео-генерации
• 3 бесплатные фото-обработки

4.3. Тарифные планы:
• ЛАЙТ — 1 990 ₽ (120 монеток, лимит 3 видео/день)
• СТАНДАРТ — 2 490 ₽ (200 монеток, лимит 5 видео/день)
• ПРО — 4 990 ₽ (400 монеток, лимит 10 видео/день)

4.6. Логика возвратов:
Возврат ресурсов осуществляется ТОЛЬКО при:
• Технических сбоях на стороне Сервиса
• Отсутствии файла в результате выполнения запроса
• Получении повреждённого или нечитаемого файла

Возврат НЕ осуществляется при:
• Субъективной неудовлетворённости качеством результата
• Несоответствии результата ожиданиям Пользователя
• Ошибках в составлении запроса со стороны Пользователя

9. ВОЗРАСТНЫЕ ОГРАНИЧЕНИЯ
9.1. Сервис предназначен для лиц, достигших 18 лет.

⚠️ ВАЖНОЕ НАПОМИНАНИЕ
Приобретая тариф и используя Сервис, вы подтверждаете:
• Ознакомление с условиями Соглашения
• Понимание технологической природы AI-генерации
• Принятие всех рисков, связанных с непредсказуемостью результатов
• Готовность нести полную ответственность за использование контента

Версия документа: 1.0
Дата вступления в силу: 01.10.2025"""
        
        await q.edit_message_text(
            terms_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="open:pricing")],
            ])
        )
        return

    if data == "back_home":
        await q.message.edit_text("Главное меню:", reply_markup=kb_home_inline())
        return

    # Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("🧠✨ Режим умного помощника активирован!")
        await q.message.reply_text("Опишите идею: умный помощник превратит её в сценарий для 8-секундного ролика ✨", reply_markup=kb_back_only()); return

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
        explanation = ("🧪 Режим для смелых экспериментов: собираем сцены и репортажи в стиле вирусных видео Антона Кудо Neurokudo!\n\nВыберите тип сюжета: умный помощник предложит готовые сценарии и фразы ✨")
        await q.message.reply_text(explanation, reply_markup=kb_nkudo_menu()); return
    if data == "back_modes":
        log.info(f"User {q.from_user.id} pressed back_modes, current mode: {st.get('mode')}")
        # Сбрасываем состояние при возврате к режимам
        st.update({"mode": None, "scene": None, "style": None, "replica": None, "awaiting_scene": False})
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "nkudo_menu_back":
        # Если есть резервная копия сцены, откатываем к ней
        if st.get("scene_backup"):
            st["scene"] = st["scene_backup"]
            st["scene_backup"] = None  # Очищаем резервную копию
            txt = "↩️ Откат к предыдущей версии\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_nkudo_single())
            return
        else:
            await q.message.edit_text("Выберите тип сюжета:", reply_markup=kb_nkudo_menu())
            return

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
            st["scene_backup"] = st["scene"]
            # Показываем загрузочное сообщение
            await q.message.edit_text("⏳ Ожидайте, сцена улучшается...")
            # Используем новую функцию, которая сохраняет фразы
            current_phrase = st.get("replica", "")
            st["scene"] = improve_scene_with_phrase(st["scene"], current_phrase, mode="complex")
            txt = "🧠✨ Сцена улучшена помощником\n\n🎬 Улучшенная сцена:\n" + st["scene"] + "\n\nОставить улучшенную версию?"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оставить", callback_data="improve_keep")],
                [InlineKeyboardButton("↩️ Отмена", callback_data="improve_cancel")],
            ])
            await q.message.edit_text(txt, reply_markup=kb); return
    if data == "improve_keep":
        # Определяем правильную клавиатуру в зависимости от режима
        if st.get("mode") == "nkudo":
            txt = "✅ Ок, оставляем улучшенную.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_nkudo_single())
        elif st.get("mode") == "lego":
            txt = "✅ Ок, оставляем улучшенную.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
        else:
            await q.message.edit_text("✅ Ок, оставляем улучшенную.", reply_markup=kb_variants())
        return
    if data == "improve_cancel":
        st["scene"] = st.get("scene_backup", st.get("scene"))
        # Определяем правильную клавиатуру в зависимости от режима
        if st.get("mode") == "nkudo":
            txt = "↩️ Вернул прежнюю.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_nkudo_single())
        elif st.get("mode") == "lego":
            txt = "↩️ Вернул прежнюю.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
        else:
            await q.message.edit_text("↩️ Вернул прежнюю.", reply_markup=kb_variants())
        return

    # NEUROKUDO — встраивание фрази в сцену
    if data == "nkudo_embed_replica":
        if st.get("scene"):
            # Показываем сообщение ожидания
            await q.message.edit_text("⏳ Ожидайте, фраза генерируется...")
            
            # Сохраняем текущую версию для отката
            st["scene_backup"] = st["scene"]
            
            # Генерируем фразу в стиле NEUROKUDO
            base_scene = st.get("scene", "")
            prompt = (
                f"Create a grandmother's dialogue in NEUROKUDO style for this scene.\n\n"
                f"Scene: {base_scene}\n\n"
                f"NEUROKUDO DIALOGUE STYLE:\n"
                f"- Grandmother (75-85 years old) speaks calmly as if incredible things are normal\n"
                f"- Village accent, simple words, sometimes with humor\n"
                f"- Reactions: pride, explanation, calmness before absurdity\n"
                f"EXAMPLES FROM NEUROKUDO (for inspiration, create NEW variations):\n"
                f"- 'Взяла вот на передержку маленьких, скоро выпустят их, пусть сил набираются'\n"
                f"- 'Да соседка бегемотов завела, я решила чем мы хуже, заказали вот малышей из Намибии'\n"
                f"- 'Аккуратнее, лАрочка, чего ты нервничаешь. Сейчас они уйдут'\n"
                f"- 'Не бойтесь её. Это Лариска. В погребе нашла, между банок сидела'\n"
                f"- 'Вот, мои несушки, кормилицы мои, каждое утро свежие яички'\n\n"
                f"TASK: Create NEW dialogue inspired by these examples, not copy them.\n"
                f"Use similar tone and style but with different words and situations.\n"
                f"Write in RUSSIAN. Format: ONE complete sentence, maximum 20 words.\n"
                f"STRICT RULE: NO DASHES, HYPHENS, OR EM DASHES (—, -, –) in the dialogue!\n"
                f"LENGTH RULE: Maximum 20 words total. Make it complete and conversational!"
            )
            
            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=35,
                    temperature=0.8,
                )
                replica = resp.choices[0].message.content.strip() if resp else "Да сама довезу без принцев обойдусь!"
            except Exception as e:
                replica = f"(⚠️ Ошибка генерации: {e})"
            
            # Очищаем фразу от тире
            replica = _clean_replica(replica)
            
            # Теперь встраиваем фразу в сцену через GPT
            embed_prompt = (
                f"Встрой фразу бабушки в описание сцены.\n\n"
                f"Исходная сцена: {base_scene}\n"
                f"Фраза бабушки: {replica}\n\n"
                f"ТРЕБОВАНИЯ:\n"
                f"- Встрой фразу естественно в подходящее место сцены\n"
                f"- Если в сцене уже есть фраза, замени её на новую\n"
                f"- Если фрази нет, добавь её в логичное место\n"
                f"- Сохрани стиль и тон описания\n"
                f"- Фраза должна быть в кавычках\n"
                f"- Сцена должна остаться целостной и логичной\n\n"
                f"Верни только обновленное описание сцены без дополнительных комментариев."
            )
            
            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": embed_prompt}],
                    max_tokens=200,
                    temperature=0.7,
                )
                updated_scene = resp.choices[0].message.content.strip() if resp else base_scene
                st["scene"] = updated_scene
                st["replica"] = replica  # Сохраняем фразу отдельно
            except Exception as e:
                updated_scene = f"{base_scene}\n\nБабушка говорит: {replica}"
                st["scene"] = updated_scene
                st["replica"] = replica
            
            # Показываем обновленную сцену
            txt = f"💬 Фраза встроена в сцену\n\n🎬 Обновленная сцена:\n{st['scene']}\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_nkudo_single())
            return

    # NEUROKUDO — репортаж (2 сцены)
    if data == "nkudo_reportage":
        await q.message.edit_text("⏳ Генерирую репортаж из деревни...")
        s1 = generate_nkudo_reportage_scene1()
        s2, rep = generate_nkudo_reportage_scene2(s1)
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2; st["replica"] = rep
        st["scene"] = f"{s1}\n\n{s2}"; st["nkudo_type"] = "reportage"
        txt = ("🔮 Сгенерирован репортаж\n\n"
               f"📺 Сцена 1: {s1}\n\n"
               f"🎤 Сцена 2: {s2}\n\n"
               f"💬 Фраза: {rep}\n\n"
               "Общая длительность ~16 сек")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_reroll_scene1":
        st["nkudo_scene1"] = generate_nkudo_reportage_scene1()
        await q.message.edit_text(f"🔄 Новая сцена 1:\n\n{st['nkudo_scene1']}", reply_markup=kb_nkudo_reportage_edit()); return
    if data == "nkudo_reroll_scene2":
        s2, rep = generate_nkudo_reportage_scene2(st.get("nkudo_scene1",""))
        st["nkudo_scene2"] = s2; st["replica"] = rep
        await q.message.edit_text(f"🔄 Новая сцена 2:\n\n{st['nkudo_scene2']}\n\n💬 Фраза: {rep}",
                                  reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_edit_scene1":
        st["editing_scene"] = 1; st["awaiting_scene_edit"] = True
        await q.message.edit_text(f"✏️ Редактирование сцены 1:\n\n{st.get('nkudo_scene1','')}\n\nОтправьте новый текст:",
                                   reply_markup=kb_scene_edit()); return
    if data == "nkudo_edit_scene2":
        st["editing_scene"] = 2; st["awaiting_scene_edit"] = True
        await q.message.edit_text(f"✏️ Редактирование сцены 2:\n\n{st.get('nkudo_scene2','')}\n\nОтправьте новый текст:",
                                   reply_markup=kb_scene_edit()); return
    if data == "scene_save":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("✅ Изменения сохранены!")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Фраза: {st.get('replica','')}")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return
    if data == "scene_cancel":
        st["awaiting_scene_edit"] = False
        await q.message.edit_text("❌ Редактирование отменено")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Фраза: {st.get('replica','')}")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return


    if data == "nkudo_regenerate_report":
        await q.message.edit_text("🔄 Генерирую новый репортаж...")
        s1 = generate_nkudo_reportage_scene1()
        s2, rep = generate_nkudo_reportage_scene2(s1)
        st["nkudo_scene1"] = s1; st["nkudo_scene2"] = s2; st["replica"] = rep
        st["scene"] = f"{s1}\n\n{s2}"
        txt = f"🔮 Новый репортаж\n\n📺 Сцена 1: {s1}\n\n🎤 Сцена 2: {s2}\n\n💬 Фраза: {rep}"
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_improve_report":
        if st.get("nkudo_scene1") and st.get("nkudo_scene2"):
            st["scene1_backup"] = st["nkudo_scene1"]; st["scene2_backup"] = st["nkudo_scene2"]
            # Показываем загрузочное сообщение
            await q.message.edit_text("⏳ Ожидайте, сцена улучшается...")
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
                   f"💬 Фраза: {st.get('replica','')}")
            await q.message.edit_text(txt, reply_markup=kb); return
    if data == "report_improve_keep":
        st["scene1_backup"] = None; st["scene2_backup"] = None
        await q.message.edit_text("✅ Улучшенная версия сохранена!")
        txt = ("📮 Текущий репортаж:\n\n"
               f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
               f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
               f"💬 Фраза: {st.get('replica','')}")
        await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return
    if data == "report_improve_cancel":
        if st.get("scene1_backup") and st.get("scene2_backup"):
            st["nkudo_scene1"] = st["scene1_backup"]; st["nkudo_scene2"] = st["scene2_backup"]
            st["scene"] = f"{st['nkudo_scene1']}\n\n{st['nkudo_scene2']}"
            st["scene1_backup"] = None; st["scene2_backup"] = None
            await q.message.edit_text("↩️ Возвращена прежняя версия!")
            txt = ("📮 Текущий репортаж:\n\n"
                   f"📺 Сцена 1: {st.get('nkudo_scene1','')}\n\n"
                   f"🎤 Сцена 2: {st.get('nkudo_scene2','')}\n\n"
                   f"💬 Фраза: {st.get('replica','')}")
            await q.message.edit_text(txt, reply_markup=kb_nkudo_reportage_edit()); return

    if data == "nkudo_approve":
        if st.get("nkudo_type") == "reportage":
            # Показываем выбор стилей для репортажа
            await q.message.edit_text("Выбери стиль для репортажа:", reply_markup=kb_styles())
            return

    # LEGO — одиночная сцена
    if data == "lego_single":
        await q.message.edit_text("⏳ Генерирую LEGO сцену...")
        st["scene"] = generate_lego_single_scene(); st["lego_type"] = "single"
        txt = "🧱 Сгенерирована LEGO сцена\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_lego_single()); return

    if data == "lego_regenerate_single":
        await q.message.edit_text("⏳ Генерирую новую LEGO сцену...")
        st["scene"] = generate_lego_single_scene()
        txt = "🧱 Новая LEGO сцена\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
        await q.message.edit_text(txt, reply_markup=kb_lego_single()); return

    if data == "lego_improve_single":
        if st.get("scene"):
            st["scene_backup"] = st["scene"]
            # Показываем загрузочное сообщение
            await q.message.edit_text("⏳ Ожидайте, сцена улучшается...")
            # Используем новую функцию, которая сохраняет фразы
            current_phrase = st.get("replica", "")
            st["scene"] = improve_scene_with_phrase(st["scene"], current_phrase, mode="complex")
            txt = "🧠✨ LEGO сцена улучшена помощником\n\n🎬 Улучшенная сцена:\n" + st["scene"] + "\n\nОставить улучшенную версию?"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оставить", callback_data="lego_improve_keep")],
                [InlineKeyboardButton("↩️ Отмена", callback_data="lego_improve_cancel")],
                [InlineKeyboardButton("🔄 Ещё раз", callback_data="lego_improve_again")],
            ])
            await q.message.edit_text(txt, reply_markup=kb); return

    if data == "lego_improve_keep":
        # Определяем правильную клавиатуру в зависимости от режима
        if st.get("mode") == "lego":
            txt = "✅ Ок, оставляем улучшенную.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
        else:
            await q.message.edit_text("✅ Ок, оставляем улучшенную.", reply_markup=kb_variants())
        return

    if data == "lego_improve_cancel":
        st["scene"] = st.get("scene_backup", st.get("scene"))
        # Определяем правильную клавиатуру в зависимости от режима
        if st.get("mode") == "lego":
            txt = "↩️ Вернул прежнюю.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
        else:
            await q.message.edit_text("↩️ Вернул прежнюю.", reply_markup=kb_variants())
        return

    if data == "lego_improve_again":
        # Используем новую функцию, которая сохраняет фразы
        current_phrase = st.get("replica", "")
        st["scene"] = improve_scene_with_phrase(st.get("scene_backup", st.get("scene", "")), current_phrase, mode="complex")
        # Определяем правильную клавиатуру в зависимости от режима
        if st.get("mode") == "lego":
            txt = "🔄 Обновил улучшенную версию.\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
        else:
            await q.message.edit_text("🔄 Обновил улучшенную версию.", reply_markup=kb_variants())
        return

    # LEGO — встраивание фрази в сцену
    if data == "lego_embed_replica":
        if st.get("scene"):
            # Показываем сообщение ожидания
            await q.message.edit_text("⏳ Ожидайте, фраза генерируется...")
            
            # Сохраняем текущую версию для отката
            st["scene_backup"] = st["scene"]
            
            # Генерируем фразу в стиле LEGO
            base_scene = st.get("scene", "")
            prompt = (
                f"Create a grandmother's dialogue in LEGO style for this scene.\n\n"
                f"Scene: {base_scene}\n\n"
                f"LEGO DIALOGUE STYLE:\n"
                f"- LEGO grandmother (75-85 years old) speaks in simple, playful way\n"
                f"- Child-like wonder, bright and cheerful tone\n"
                f"- Reactions: excitement, pride, simple explanations\n"
                f"EXAMPLES FROM LEGO STYLE (for inspiration, create NEW variations):\n"
                f"- 'Вот мои LEGO питомцы, они самые лучшие в мире!'\n"
                f"- 'Смотри, как красиво получилось из LEGO кирпичиков!'\n"
                f"- 'Это мой LEGO сад, здесь растут LEGO цветочки!'\n"
                f"- 'LEGO котик очень умный, он знает все секреты!'\n"
                f"- 'Вот так строим из LEGO, по кирпичику за раз!'\n\n"
                f"TASK: Create NEW dialogue inspired by these examples, not copy them.\n"
                f"Use similar tone and style but with different words and situations.\n"
                f"Write in RUSSIAN. Format: ONE complete sentence, maximum 20 words.\n"
                f"STRICT RULE: NO DASHES, HYPHENS, OR EM DASHES (—, -, –) in the dialogue!\n"
                f"LENGTH RULE: Maximum 20 words total. Make it complete and conversational!"
            )
            
            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=35,
                    temperature=0.8,
                )
                replica = resp.choices[0].message.content.strip() if resp else "Да сама довезу без принцев обойдусь!"
            except Exception as e:
                replica = f"(⚠️ Ошибка генерации: {e})"
            
            # Очищаем фразу от тире
            replica = _clean_replica(replica)
            
            # Теперь встраиваем фразу в сцену через GPT
            embed_prompt = (
                f"Встрой фразу LEGO бабушки в описание LEGO сцены.\n\n"
                f"Исходная сцена: {base_scene}\n"
                f"Фраза LEGO бабушки: {replica}\n\n"
                f"ТРЕБОВАНИЯ:\n"
                f"- Встрой фразу естественно в подходящее место LEGO сцены\n"
                f"- Если в сцене уже есть фраза, замени её на новую\n"
                f"- Если фрази нет, добавь её в логичное место\n"
                f"- Сохрани LEGO стиль и тон описания\n"
                f"- Фраза должна быть в кавычках\n"
                f"- Сцена должна остаться целостной и логичной\n\n"
                f"Верни только обновленное описание LEGO сцены без дополнительных комментариев."
            )
            
            try:
                if not gpt:

                    replica = "Да сама довезу без принцев обойдусь!"

                else:

                    resp = gpt.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": embed_prompt}],
                    max_tokens=200,
                    temperature=0.7,
                )
                updated_scene = resp.choices[0].message.content.strip() if resp else base_scene
                st["scene"] = updated_scene
                st["replica"] = replica  # Сохраняем фразу отдельно
            except Exception as e:
                updated_scene = f"{base_scene}\n\nLEGO бабушка говорит: {replica}"
                st["scene"] = updated_scene
                st["replica"] = replica
            
            # Показываем обновленную сцену
            txt = f"💬 Фраза встроена в LEGO сцену\n\n🎬 Обновленная сцена:\n{st['scene']}\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
            return

    # LEGO — репортаж
    if data == "lego_reportage":
        await q.message.edit_text("⏳ Генерирую LEGO репортаж...")
        s1 = generate_lego_reportage_scene1()
        s2, rep = generate_lego_reportage_scene2(s1)
        st["lego_scene1"] = s1; st["lego_scene2"] = s2; st["replica"] = rep
        st["scene"] = f"{s1}\n\n{s2}"; st["lego_type"] = "reportage"
        txt = f"🧱 LEGO репортаж готов\n\n📺 Сцена 1: {s1}\n\n🎤 Сцена 2: {s2}\n\n💬 Фраза: {rep}"
        await q.message.edit_text(txt, reply_markup=kb_lego_single()); return

    if data == "lego_menu_back":
        # Если есть резервная копия сцены, откатываем к ней
        if st.get("scene_backup"):
            st["scene"] = st["scene_backup"]
            st["scene_backup"] = None  # Очищаем резервную копию
            txt = "↩️ Откат к предыдущей версии\n\n🎬 Сцена (8 сек):\n" + st["scene"] + "\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_lego_single())
            return
        else:
            await q.message.edit_text("Выберите тип сюжета:", reply_markup=kb_lego_menu())
            return

    # --- Примерочная: кнопки флоу ---

    if data == "tryon_swap":
        stt = st["tryon"]
        stt["person"], stt["garment"] = stt.get("garment"), stt.get("person")
        if not stt.get("person") or not stt.get("garment"):
            await q.message.edit_text("Нужно два изображения: человек и одежда. Пришлите недостающее.",
                                      reply_markup=kb_tryon_need_garment())
            return
        await q.message.edit_text("Роли поменяли местами.\n\nФото получены. Готовы примерять?",
                                  reply_markup=kb_tryon_confirm("② → ①", st.get("tryon_bonus", 0)))
        stt["stage"] = "confirm"
        return

    if data == "tryon_reset":
        st["tryon"] = {"stage": "await_person", "person": None, "garment": None, "dressed": None, "await_bg": False, "await_prompt": False}
        await q.message.edit_text("Сбросил. Пришлите фото человека.", reply_markup=kb_tryon_start())
        return

    if data == "tryon_confirm":
        stt = st["tryon"]
        if not stt.get("person") or not stt.get("garment"):
            await q.message.reply_text("Нужно два изображения: человек и одежда. Пришлите недостающее.",
                                       reply_markup=kb_tryon_need_garment())
            return
        
        # Проверяем ресурсы (бонусы или монеты)
        tryon_bonus = st.get("tryon_bonus", 0)
        coins = st.get("coins", 0)
        
        if tryon_bonus == 0 and coins < COST_TRYON:
            await q.message.reply_text(
                f"❌ Не хватает ресурсов для примерочной.\n\n"
                f"🎁 Бонусных примерок: {tryon_bonus}\n"
                f"💰 Монеток: {coins} (нужно: {COST_TRYON})\n\n"
                f"💳 Докупить монеты?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚡ Быстрые докупки", callback_data="show_addons")],
                    [InlineKeyboardButton("📚 Тарифы", callback_data="open:pricing")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
                ])
            )
            return
        
        # Списываем ресурсы (бонусы или монеты)
        if tryon_bonus > 0:
            st["tryon_bonus"] -= 1
            cost_text = "0 монеток (бонус)"
        else:
            st["coins"] -= COST_TRYON
            cost_text = f"{COST_TRYON} монеток"
        
        await q.message.edit_text("⏳ Делаю примерку…")
        try:
            result_bytes = await asyncio.to_thread(virtual_tryon, stt["person"], stt["garment"], 1)
            stt["dressed"] = result_bytes
            await q.message.edit_media(media=InputMediaPhoto(media=result_bytes, caption=f"✅ Готово! Одежда перенесена на человека.\n💰 Списано: {cost_text}"), reply_markup=kb_tryon_after())
            stt["stage"] = "after"
        except Exception as e:
            log.exception("VTO failed")
            # Возвращаем ресурсы при ошибке
            if tryon_bonus > 0:
                st["tryon_bonus"] += 1
            else:
                st["coins"] += COST_TRYON
            await q.message.reply_text(f"⚠️ Ошибка примерочной: {e}")
            await q.message.reply_text("Возврат в меню:", reply_markup=kb_home_inline())
        return

    # --- AFTER RESULT ACTIONS ---
    if data == "tryon_new_pose":
        stt = st["tryon"]
        stt["stage"] = "await_person"
        await q.message.edit_text(
            "🔄 Другая поза.\nПришлите новое фото человека в желаемой позе/ракурсе.",
            reply_markup=kb_tryon_need_garment()
        )
        return

    if data == "tryon_new_garment":
        stt = st["tryon"]
        stt["stage"] = "await_garment"
        await q.message.edit_text(
            "👗 Другая одежда.\nПришлите фото новой одежды на нейтральном фоне.",
            reply_markup=kb_tryon_need_garment()
        )
        return

    if data == "tryon_new_bg":
        stt = st["tryon"]
        stt["await_bg"] = True
        await q.message.edit_text(
            "🏞 Новая локация.\nПришлите фон-картинку (фото места), куда поместить одетую модель.",
            reply_markup=kb_tryon_after()
        )
        return

    if data == "tryon_prompt":
        stt = st["tryon"]
        stt["await_prompt"] = True
        await q.message.edit_text(
            "✍️ Опишите кратко позу/локацию (например: «сидит на лавочке, двор в деревне, закат»).\n"
            "Это экспериментальная функция — возможны лёгкие изменения лица.",
            reply_markup=kb_tryon_after()
        )
        return

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
        log.info(f"User {q.from_user.id} pressed go_next, current mode: {st.get('mode')}, scene: {st.get('scene', 'None')[:50]}...")
        # Для всех режимов показываем выбор стилей
        if st.get("scene"): 
            await q.message.edit_text(f"✅ Сцена готова:\n\n{st['scene']}\n\nВыбери стиль:", reply_markup=kb_styles())
        else:
            log.warning(f"User {q.from_user.id} pressed go_next but no scene found")
            await q.message.edit_text("Выбери стиль:", reply_markup=kb_styles())
        return

    # --- Обработка стилей ---
    if data.startswith("style_") or data == "style_None":
        if data != "style_None":
            st["style"] = data.replace("style_", "").replace("_", " ")
        
        # Убираем меню стилей и показываем следующее меню
        # Для всех режимов переходим к выбору ориентации
        await q.message.edit_text("Выбери ориентацию:", reply_markup=kb_orientation())
        return

    # --- Ручной ввод фрази ---
    if data == "manual_replica":
        st["awaiting_manual_replica"] = True
        await q.message.edit_text(
            "Введи текст фрази одним сообщением:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data="cancel_manual_replica")]
            ])
        )
        return

    # --- Отмена ручного ввода фрази ---
    if data == "cancel_manual_replica":
        st["awaiting_manual_replica"] = False
        # Возвращаемся к предыдущему меню
        if st.get("mode") == "nkudo":
            # Для режима NEUROKUDO - показываем промт в повествовательном формате
            scene_text = st.get('scene','')
            txt = f"✅ Стиль выбран: {st.get('style', 'без стиля')}\n\n🎬 Сцена:\n{scene_text}\n\nЧто делаем дальше?"
            await q.message.edit_text(txt, reply_markup=kb_after_style())
        else:
            # Для обычных режимов
            await q.message.edit_text("Что делаем дальше?", reply_markup=kb_after_style())
        return

    # --- Дополнить итоговый промт ---
    if data == "prompt_add":
        st["awaiting_prompt_add"] = True
        await q.message.reply_text("Что добавить к сцене? Напиши 1–2 короткие фразы:")
        return

    # --- Редактирование фрази в финальном чеке ---
    if data == "edit_replica_final":
        st["awaiting_manual_replica"] = True
        st["from_final_check"] = True  # Флаг что пришли из финального чека
        current_replica = st.get("replica", "")
        await q.message.reply_text(
            f"✍️ Редактирование фрази\n\n"
            f"Текущая фраза: {current_replica}\n\n"
            f"Введите новую фразу:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_final")]])
        )
        return

    # --- Возврат к финальному чеку ---
    if data == "back_to_final":
        st["from_final_check"] = False
        # Восстанавливаем финальный чек
        parts = [f"✅ Сцена: {st.get('scene','')}"]
        # Для LEGO режима не показываем стиль, так как он автоматический
        if st.get("style") and st.get("mode") != "lego": parts.append(f"✅ Стиль: {st['style']}")
        if st.get("replica"): parts.append(f"✅ Фраза: {st['replica']}")
        if st.get("orientation"): parts.append(f"✅ Ориентация: {st['orientation']}")

        preview = "📝 Итоговый промт для генерации:\n\n" + "\n\n".join(parts)

        kb_preview = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
            [InlineKeyboardButton("💬 Изменить фразу", callback_data="edit_replica_final")],
            [InlineKeyboardButton("🎲 Сгенерировать фразу", callback_data="generate_replica_final")],
            [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
        ])

        await q.message.edit_text(preview, reply_markup=kb_preview)
        return

    # --- Генерация фрази в финальном чеке ---
    if data == "generate_replica_final":
        # Показываем сообщение ожидания
        await q.message.edit_text("⏳ Ожидайте, фраза генерируется...")
        
        base_scene = st.get("scene", "")
        style_note = st.get("style") or "без стиля"

        if st.get("mode") == "nkudo":
            # Специальный промпт для NEUROKUDO
                prompt = (
                f"Write grandmother's dialogue in NEUROKUDO style for this scene.\n\n"
                f"Scene: {base_scene}\n"
                f"Style: {style_note}\n\n"
                f"NEUROKUDO DIALOGUE STYLE:\n"
                f"- Grandmother (75-85 years old) speaks calmly as if incredible things are normal\n"
                f"- Village accent, simple words, sometimes with humor\n"
                f"- Reactions: pride, explanation, calmness before absurdity\n"
                f"EXAMPLES FROM NEUROKUDO (for inspiration, create NEW variations):\n"
                f"- 'Взяла вот на передержку маленьких, скоро выпустят их, пусть сил набираются'\n"
                f"- 'Да соседка бегемотов завела, я решила чем мы хуже, заказали вот малышей из Намибии'\n"
                f"- 'Аккуратнее, лАрочка, чего ты нервничаешь. Сейчас они уйдут'\n"
                f"- 'Не бойтесь её. Это Лариска. В погребе нашла, между банок сидела'\n"
                f"- 'Вот, мои несушки, кормилицы мои, каждое утро свежие яички'\n\n"
                f"TASK: Create NEW dialogue inspired by these examples, not copy them.\n"
                f"Use similar tone and style but with different words and situations.\n"
                f"Write in RUSSIAN. Format: ONE complete sentence, maximum 20 words.\n"
                f"STRICT RULE: NO DASHES, HYPHENS, OR EM DASHES (—, -, –) in the dialogue!\n"
                f"LENGTH RULE: Maximum 20 words total. Make it complete and conversational!"
            )
        else:
            # Обычный промпт для других режимов
                prompt = (
                f"Напиши короткую и выразительную фразу для сцены.\n\n"
                f"Сцена: {base_scene}\n"
                f"Стиль: {style_note}\n\n"
                f"Формат: ОДНО полное предложение, максимум 20 слов.\n"
                f"СТРОГО ЗАПРЕЩЕНО: никаких тире, дефисов или длинных тире (—, -, –) в фразе!\n"
                f"ДЛИНА: максимум 20 слов. Делай завершенным и разговорно!"
            )

        try:
            if not gpt:

                replica = "Да сама довезу без принцев обойдусь!"

            else:

                resp = gpt.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=35,
                temperature=0.8,
            )
            replica = resp.choices[0].message.content.strip() if resp else "Да сама довезу без принцев обойдусь!"
        except Exception as e:
            replica = f"(⚠️ Ошибка генерации: {e})"

        # Очищаем фразу от тире
        replica = _clean_replica(replica)
        st["replica"] = replica

        # Возвращаемся к финальному чеку
        parts = [f"✅ Сцена: {st.get('scene','')}"]
        # Для LEGO режима не показываем стиль, так как он автоматический
        if st.get("style") and st.get("mode") != "lego": parts.append(f"✅ Стиль: {st['style']}")
        if st.get("replica"): parts.append(f"✅ Фраза: {st['replica']}")
        if st.get("orientation"): parts.append(f"✅ Ориентация: {st['orientation']}")

        preview = "📝 Итоговый промт для генерации:\n\n" + "\n\n".join(parts)

        kb_preview = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Дополнить", callback_data="prompt_add")],
            [InlineKeyboardButton("💬 Изменить фразу", callback_data="edit_replica_final")],
            [InlineKeyboardButton("🎲 Сгенерировать фразу", callback_data="generate_replica_final")],
            [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")]
        ])

        await q.message.edit_text(preview, reply_markup=kb_preview)
        return

    # --- Генерация фрази ---
    if data == "generate_replica":
        # Показываем сообщение ожидания
        await q.message.edit_text("⏳ Ожидайте, фраза генерируется...")
        
        base_scene = st.get("scene", "")
        style_note = st.get("style") or "без стиля"

        if st.get("mode") == "nkudo":
            # Специальный промпт для NEUROKUDO
                prompt = (
                f"Write grandmother's dialogue in NEUROKUDO style for this scene.\n\n"
                f"Scene: {base_scene}\n"
                f"Style: {style_note}\n\n"
                f"NEUROKUDO DIALOGUE STYLE:\n"
                f"- Grandmother (75-85 years old) speaks calmly as if incredible things are normal\n"
                f"- Village accent, simple words, sometimes with humor\n"
                f"- Reactions: pride, explanation, calmness before absurdity\n"
                f"EXAMPLES FROM NEUROKUDO (for inspiration, create NEW variations):\n"
                f"- 'Взяла вот на передержку маленьких, скоро выпустят их, пусть сил набираются'\n"
                f"- 'Да соседка бегемотов завела, я решила чем мы хуже, заказали вот малышей из Намибии'\n"
                f"- 'Аккуратнее, лАрочка, чего ты нервничаешь. Сейчас они уйдут'\n"
                f"- 'Не бойтесь её. Это Лариска. В погребе нашла, между банок сидела'\n"
                f"- 'Вот, мои несушки, кормилицы мои, каждое утро свежие яички'\n\n"
                f"TASK: Create NEW dialogue inspired by these examples, not copy them.\n"
                f"Use similar tone and style but with different words and situations.\n"
                f"Write in RUSSIAN. Format: ONE complete sentence, maximum 20 words.\n"
                f"STRICT RULE: NO DASHES, HYPHENS, OR EM DASHES (—, -, –) in the dialogue!\n"
                f"LENGTH RULE: Maximum 20 words total. Make it complete and conversational!"
            )
        else:
            # Обычный промпт для других режимов
            prompt = (
            f"Напиши короткую и выразительную фразу для сцены.\n\n"
            f"Сцена: {base_scene}\n"
            f"Стиль: {style_note}\n\n"
                f"Формат: ОДНО полное предложение, максимум 20 слов.\n"
                f"СТРОГО ЗАПРЕЩЕНО: никаких тире, дефисов или длинных тире (—, -, –) в фразе!\n"
                f"ДЛИНА: максимум 20 слов. Делай завершенным и разговорно!"
        )

        try:
            if not gpt:

                replica = "Да сама довезу без принцев обойдусь!"

            else:

                resp = gpt.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=35,
                temperature=0.8,
            )
            replica = resp.choices[0].message.content.strip() if resp else "Да сама довезу без принцев обойдусь!"
        except Exception as e:
            replica = f"(⚠️ Ошибка генерации: {e})"

        # Очищаем фразу от тире
        replica = _clean_replica(replica)
        st["replica"] = replica
        
        # Убираем предыдущее меню и показываем новое
        if st.get("mode") == "nkudo":
            # Для режима NEUROKUDO показываем промт в повествовательном формате
            scene_text = st.get('scene','')
            txt = f"✅ Создана фраза: {replica}\n\n🎬 Сцена:\n{scene_text}\n\nТеперь можно изменить или продолжить:"
        else:
            # Для обычного режима встраиваем фразу в сцену
            if st.get("scene"):
                # Встраиваем фразу в сцену через GPT
                embed_prompt = (
                    f"Встрой фразу в описание сцены как речь персонажа.\n\n"
                    f"Исходная сцена: {st['scene']}\n"
                    f"Фраза: {replica}\n\n"
                    f"ТРЕБОВАНИЯ:\n"
                    f"- Встрой фразу как прямую речь персонажа в кавычках\n"
                    f"- Добавь слова автора типа 'говорит', 'восклицает', 'шепчет' и т.д.\n"
                    f"- Фраза должна звучать естественно в контексте сцены\n"
                    f"- Сцена должна остаться целостной и логичной\n\n"
                    f"Верни только обновленное описание сцены без дополнительных комментариев."
                )
                
                try:
                    if not gpt:

                        replica = "Да сама довезу без принцев обойдусь!"

                    else:

                        resp = gpt.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[{"role": "user", "content": embed_prompt}],
                        max_tokens=200,
                        temperature=0.7,
                    )
                    updated_scene = resp.choices[0].message.content.strip() if resp else base_scene
                    st["scene"] = updated_scene
                except Exception as e:
                    updated_scene = f"{st['scene']}\n\nБабушка говорит: {replica}"
                    st["scene"] = updated_scene
                
                txt = f"💬 Фраза встроена в сцену\n\n🎬 Обновленная сцена:\n{st['scene']}\n\nЧто делаем дальше?"
            else:
                txt = f"✅ Создана фраза: {replica}\n\nТеперь можно изменить или продолжить:"
        
        # Определяем правильную клавиатуру
        if st.get("mode") == "nkudo":
            await q.message.edit_text(
                txt,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
                    [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")]
                ])
            )
        else:
            # Для обычного режима показываем клавиатуру с фразой
            if st.get("scene"):
                await q.message.edit_text(txt, reply_markup=kb_variants_with_phrase())
            else:
                await q.message.edit_text(
                    txt,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✍️ Ввести фразу вручную", callback_data="manual_replica")],
                        [InlineKeyboardButton("➡️ Далее", callback_data="go_orientation")]
                    ])
                )
        return


    # --- Переход к выбору ориентации ---
    if data == "go_orientation":
        await q.message.edit_text("Выбери ориентацию:", reply_markup=kb_orientation())
        return

    # --- Выбор ориентации ---
    if data in ("ori_916", "ori_169"):
        st["orientation"] = "9:16" if data == "ori_916" else "16:9"
        await q.message.edit_text("Выбери настройки аудио:", reply_markup=kb_audio_choice())
        return
    
    # --- Выбор аудио ---
    if data in ("audio_on", "audio_off"):
        st["with_audio"] = data == "audio_on"
        
        # Показываем финальное меню с настройками
        audio_status = "🔊 С аудио" if st["with_audio"] else "🔇 Без аудио"
        orientation_status = "📱 Вертикальное (9:16)" if st["orientation"] == "9:16" else "🖥 Горизонтальное (16:9)"
        
        preview_text = (
            f"📝 Итоговые настройки:\n\n"
            f"✅ Сцена: {st.get('scene', 'Не задана')[:100]}...\n"
            f"✅ Ориентация: {orientation_status}\n"
            f"✅ Аудио: {audio_status}\n"
            f"✅ Стиль: {st.get('style', DEFAULT_STYLE)}\n\n"
            f"Готов к генерации!"
        )
        
        await q.message.edit_text(preview_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")],
            [InlineKeyboardButton("✍️ Изменить сцену", callback_data="prompt_add")],
            [InlineKeyboardButton("🔄 Переделать", callback_data="go_next")],
        ]))
        return

    # --- Отмена процедуры ---
    if data == "cancel_procedure":
        # Очищаем все данные и возвращаемся в главное меню
        st.update({"scene": None, "style": None, "replica": None, "orientation": None, "mode": None, "with_audio": DEFAULT_AUDIO})
        await q.message.edit_text("❌ Процедура отменена. Возврат в главное меню.", reply_markup=kb_home_inline())
        return

    # ГЕНЕРАЦИЯ (обычные режимы)
    if data == "generate_now":
        if not st.get("scene"): await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None: st["style"] = DEFAULT_STYLE
        if not st.get("orientation"): st["orientation"] = DEFAULT_ORIENTATION

        # Проверяем ресурсы (бонусы или монеты)
        if not can_generate_video(st):
            video_bonus = st.get("video_bonus", 0)
            coins = st.get("coins", 0)
            
            if video_bonus == 0 and coins < COST_VIDEO:
                await q.message.reply_text(
                    f"❌ Не хватает ресурсов для генерации видео.\n\n"
                    f"🎁 Бонусных видео: {video_bonus}\n"
                    f"💰 Монеток: {coins} (нужно: {COST_VIDEO})\n\n"
                    f"💳 Докупить монеты?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚡ Быстрые докупки", callback_data="show_addons")],
                        [InlineKeyboardButton("📚 Тарифы", callback_data="open:pricing")],
                        [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
                    ])
                )
                return

        # Проверяем дневной лимит
        if not check_daily_cap(st, "video"):
            videos_left = get_daily_videos_left(st)
            plan = st.get("plan", "light")
            plan_name = PLANS[plan]["name"]
            await q.message.reply_text(
                f"❌ Дневной лимит видео исчерпан.\n"
                f"План {plan_name}: {DAILY_CAP_VIDEOS[plan]} видео в день.\n\n"
                f"Попробуйте завтра или смените тарифный план.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Сменить тариф", callback_data="open:pricing")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back_home")],
                ])
            )
            return

        # Создаем задачу
        try:
            job_id = hold_and_start(st, "video")
            st["current_job_id"] = job_id
        except Exception as e:
            await q.message.reply_text(f"❌ Ошибка создания задачи: {str(e)}")
            return

        msg = await q.message.reply_text(
            f"⏳ Генерирую видео… Это может занять несколько минут.\n"
            f"💰 Списано: {COST_VIDEO} монеток"
        )
        try:
            # REPORTAGE — два видео подряд
            if st.get("nkudo_type") == "reportage" or st.get("mode") == "reportage":
                prompt1 = to_json_prompt(
                    st.get("nkudo_scene1",""), st.get("style"), None, "reportage",
                    aspect_ratio=st["orientation"], context=None
                )
                prompt2 = to_json_prompt(
                    st.get("nkudo_scene2",""), st.get("style"), st.get("replica"), "reportage",
                    aspect_ratio=st["orientation"], context=st.get("nkudo_scene1")
                )

                res1 = await asyncio.to_thread(generate_video_sync, prompt1, duration=8, aspect_ratio=st["orientation"], with_audio=st.get("with_audio", True))
                vids1 = (res1 or {}).get("videos", [])
                if vids1 and vids1[0].get("file_path") and os.path.exists(vids1[0]["file_path"]):
                    with open(vids1[0]["file_path"], "rb") as f:
                        await q.message.reply_video(video=f, caption="📺 Сцена 1", supports_streaming=True)
                else:
                    await q.message.reply_text("⚠️ Сцена 1: видео не вернулось.")

                res2 = await asyncio.to_thread(generate_video_sync, prompt2, duration=8, aspect_ratio=st["orientation"], with_audio=st.get("with_audio", True))
                vids2 = (res2 or {}).get("videos", [])
                cap2 = "🎤 Сцена 2" + (f"\n💬 {st.get('replica')}" if st.get("replica") else "")
                if vids2 and vids2[0].get("file_path") and os.path.exists(vids2[0]["file_path"]):
                    with open(vids2[0]["file_path"], "rb") as f:
                        await q.message.reply_video(video=f, caption=cap2, supports_streaming=True)
                else:
                    await q.message.reply_text("⚠️ Сцена 2: видео не вернулось.")

                # Отмечаем задачу как успешную
                if st.get("current_job_id"):
                    on_success(st, st["current_job_id"])
                
                await q.message.reply_text("Готово! Что дальше?", reply_markup=kb_video_result())
                await q.message.reply_text("Быстрые кнопки внизу активны.", reply_markup=reply_main_kb())
                return

            # Обычные — одно видео
            prompt = to_json_prompt(
                st["scene"], st.get("style"), st.get("replica"), st.get("mode"),
                aspect_ratio=st["orientation"], context=None
            )
            res = await asyncio.to_thread(generate_video_sync, prompt, duration=8, aspect_ratio=st["orientation"], with_audio=st.get("with_audio", True))
            videos = (res or {}).get("videos", [])
            if not videos:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home_inline())
                return

            v0 = videos[0]; file_path = v0.get("file_path"); uri = v0.get("uri")
            caption = (f"✅ Видео готово!\n\n🎬 Сцена: {st['scene']}\n🎨 Стиль: {st['style']}" +
                       (f"\n💬 Фраза: {st['replica']}" if st.get("replica") else "") +
                       f"\n📐 Ориентация: {st['orientation']}")
            
            # Отмечаем задачу как успешную
            if st.get("current_job_id"):
                on_success(st, st["current_job_id"])
            
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await q.message.reply_video(video=f, caption=caption, supports_streaming=True, reply_markup=kb_video_result())
            elif uri:
                await q.message.reply_text(f"{caption}\n\n🔗 GCS: {uri}", reply_markup=kb_video_result())
            else:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуйте ещё раз.", reply_markup=kb_home_inline())

        except Exception as e:
            # Возвращаем монеты при ошибке
            if st.get("current_job_id"):
                on_error(st, st["current_job_id"])
            log.exception("Generation failed")
            log.exception("Veo generation failed")
            await q.message.reply_text(f"⚠️ Ошибка генерации: {e}\n\nМонетки возвращены. Попробуйте ещё раз.", reply_markup=kb_home_inline())
        finally:
            try: await msg.delete()
            except: pass
        return

    # --- JSON PRO ---
    if data == "jsonpro_enter":
        st["jsonpro"]["await_text"] = True
        await q.message.edit_text("Введи текст сцены. Я соберу полноценный JSON для Veo.",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_home")]]))
        return
    if data == "jsonpro_ori_916":
        st["jsonpro"]["orientation"] = "9:16"
        await q.message.edit_text("✅ Ориентация (JSON-режим): Вертикальное (9:16)",
                                  reply_markup=kb_jsonpro_after_text())
        return
    if data == "jsonpro_ori_169":
        st["jsonpro"]["orientation"] = "16:9"
        await q.message.edit_text("✅ Ориентация (JSON-режим): Горизонтальное (16:9)",
                                  reply_markup=kb_jsonpro_after_text())
        return
    if data == "jsonpro_generate":
        jj = st["jsonpro"].get("last_json")
        if not jj:
            await q.message.edit_text("Сначала введи текст сцены, чтобы собрать JSON.",
                                      reply_markup=kb_jsonpro_start()); return
        orr = st["jsonpro"].get("orientation", DEFAULT_ORIENTATION)
        msg = await q.message.reply_text("⏳ Генерирую видео по JSON…")
        try:
            res = await asyncio.to_thread(generate_video_sync, jj, duration=8, aspect_ratio=orr, with_audio=st.get("with_audio", True))
            videos = (res or {}).get("videos", [])
            if not videos:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуй ещё раз.", reply_markup=kb_home_inline())
                return
            v0 = videos[0]; file_path = v0.get("file_path"); uri = v0.get("uri")
            caption = f"✅ Видео по JSON готово!\n📐 Ориентация: {orr}"
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await q.message.reply_video(video=f, caption=caption, supports_streaming=True, reply_markup=kb_after_video())
            elif uri:
                await q.message.reply_text(f"{caption}\n\n🔗 GCS: {uri}", reply_markup=kb_after_video())
            else:
                await q.message.reply_text("⚠️ Видео не вернулось. Попробуй ещё раз.", reply_markup=kb_home_inline())
        except Exception as e:
            await q.message.reply_text(f"⚠️ Ошибка генерации: {e}", reply_markup=kb_home_inline())
        finally:
            try: await msg.delete()
            except: pass
        return

    # Пост-кнопки после видео
    if data == "edit_from_last":
        st["awaiting_scene"] = True
        await q.message.edit_text("✏️ Отправьте новый текст сцены. Текущая версия ниже.")
        await q.message.edit_text(f"Текущая сцена:\n\n{st.get('scene','')}", reply_markup=kb_back_only())
        return

    if data == "refine_prompt":
        st["awaiting_prompt_refine"] = True
        current_scene = st.get('scene', '')
        current_style = st.get('style', '')
        current_replica = st.get('replica', '')
        
        await q.message.edit_text(
            f"🔧 Доработка промта\n\n"
            f"Текущий промт:\n"
            f"📝 Сцена: {current_scene}\n"
            f"🎨 Стиль: {current_style}\n"
            f"💬 Фраза: {current_replica}\n\n"
            f"Напишите что нужно изменить или добавить:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_home")]])
        )
        return

    # fallback
    await q.message.reply_text("Команда пока не поддерживается. Возврат в меню.", reply_markup=kb_home_inline())

# -----------------------------------------------------------------------------
# СЛУЖЕБНОЕ: мем-сцена
# -----------------------------------------------------------------------------
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

# ----------------------------------------------------------------------------- 
# ЗАПУСК
# -----------------------------------------------------------------------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN / BOT_TOKEN")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whereami", cmd_whereami))  # утилита
    app.add_handler(CommandHandler("terms", cmd_terms))  # пользовательское соглашение
    app.add_handler(CommandHandler("test_payment", cmd_test_payment))  # тестовая команда
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))  # приём фото (примерочная)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    
    log.info("Bot is running…")
    # Запускаем polling с автоматическим удалением webhook
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

