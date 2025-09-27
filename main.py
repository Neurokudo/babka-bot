# main.py – меню, помощник, NEUROKUDO, мем-рандом, стили, реплика, генерация Veo
import os
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
    # Убираем базовые кавычки и тире для чистоты текста
    # Удаляем только основные ASCII символы, чтобы избежать проблем с юникодом
    text = text.replace('"', '')  # двойные кавычки
    text = text.replace("'", '')  # одинарные кавычки  
    text = text.replace('-', '')  # дефис
    text = text.replace('_', ' ')  # подчеркивание на пробел
    
    # Убираем лишние пробелы
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
        "absurd": "Сделай сцену более абсурдной и смешной."  # только для мемного режима
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
    sys = "Придумай короткую реплику героя к сцене, 4–10 слов. Только сама фраза. Без кавычек и тире."
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ========= NEUROKUDO режим =========
NKUDO_SYSTEM = (
    "Ты редактор видеосцен в фирменном стиле NEUROKUDO. "
    "Пиши сухо и конкретно. 8 секунд экранного времени, максимум два плана. "
    "Обязательные приёмы: 1) переворот ожиданий; 2) контраст официоза и народной речи; "
    "3) лёгкая эскалация абсурда при правдоподобии; 4) фоновая немая шутка в кадре; "
    "5) финальная короткая ласково грубая реплика бабки. "
    "Никаких кавычек и тире, никаких титров или текста в кадре."
)

def nkudo_scene(user_text: str) -> tuple[str, Optional[str]]:
    usr = (
        "Черновик пользователя: " + user_text.strip() + "\n\n"
        "Дай:\n"
        "A) СЦЕНУ – 3–5 коротких предложений, описывающих действия и кадр. "
        "Укажи где план 1 и где план 2 если он есть. Без эмо-литературы.\n"
        "B) РЕПЛИКУ – одна короткая фраза персонажа в конце, без кавычек и тире."
    )
    resp = _gpt(NKUDO_SYSTEM, usr, temperature=0.55, max_tokens=260) or user_text
    scene, replica = resp, None
    if "B)" in resp:
        parts = resp.split("B)")
        scene = parts[0].replace("A)", "").strip()
        replica = parts[1].strip()
    return _sanitize(scene), (_sanitize(replica) if replica else None)

def nkudo_refine(scene_text: str, mode: str) -> str:
    hint = "Сделай вариант проще и короче" if mode == "simple" else "Усиль абсурд, но оставь правдоподобие"
    usr = f"Сцена:\n{scene_text}\n\nТребование: {hint}. Верни только текст сцены (без пометок A/B)."
    out = _gpt(NKUDO_SYSTEM, usr, temperature=0.6 if mode == "simple" else 0.85, max_tokens=200)
    return out or _sanitize(scene_text)

def nkudo_replica(scene: str) -> str:
    sys = ("Сгенери одну короткую реплику бабки для конца сцены. "
           "Стиль: ласковая грубость, народная смекалка, без оскорблений по группам. "
           "Без тире и кавычек. 3–8 слов.")
    return _gpt(sys, "Сцена:\n" + scene, temperature=0.8, max_tokens=30) or "Поехали уже"

# ========= VEO (реальная генерация) =========
# Временно отключаем импорт пока не установлены библиотеки
# from veo_client import generate_video_sync

# Заглушка для тестирования
def generate_video_sync(prompt: str, style: Optional[str], replica: Optional[str], duration_sec: int) -> str:
    # Временная заглушка - возвращаем путь к несуществующему файлу
    # В реальности здесь должна быть генерация видео
    import tempfile
    tmp = tempfile.NamedTemporaryFile(prefix="veo_", suffix=".mp4", delete=False)
    tmp.close()
    return tmp.name

# ========= СОСТОЯНИЕ =========
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        users[uid] = {
            "mode": None,
            "source_text": None,   # исходный ввод пользователя
            "scene": None,         # текущая сцена
            "style": None,
            "replica": None,
            "awaiting_scene": False,
            "awaiting_custom_style": False,
        }

# ========= КЛАВИАТУРЫ =========
def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создание видео с помощником", callback_data="menu_make")],
        [InlineKeyboardButton("🖼️ Оживление изображения", callback_data="menu_alive")],
        [InlineKeyboardButton("📚 Гайды / Оплата", callback_data="menu_guides")],
        [InlineKeyboardButton("💤 Профиль / Баланс", callback_data="menu_profile")],
    ])

def kb_modes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠✨ Умный помощник", callback_data="mode_helper")],
        [InlineKeyboardButton("🧪 Как у NEUROKUDO", callback_data="mode_nkudo")],
        [InlineKeyboardButton("✏️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_variants():
    """Обычные варианты для режима помощника"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Усложни", callback_data="var_complex"),
         InlineKeyboardButton("✂️ Упрости", callback_data="var_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
    ])

def kb_variants_nkudo():
    """Варианты для NEUROKUDO режима"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="var_absurd"),
         InlineKeyboardButton("✂️ Проще", callback_data="var_simple")],
        [InlineKeyboardButton("🔄 Заново", callback_data="var_again"),
         InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
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

def kb_final_prompt():
    """Кнопки для финального просмотра промпта"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Создать видео", callback_data="generate_now")],
        [InlineKeyboardButton("🔄 Переделать", callback_data="go_next")],
    ])

def kb_meme():
    """Специальная клавиатура для мемного режима"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить ещё", callback_data="meme_again")],
        [InlineKeyboardButton("🧠✨ Улучшить с помощником", callback_data="meme_to_helper")],
        [InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
    ])

# ========= МЕМНЫЙ РЕЖИМ (осмысленный) =========
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

    t = random.choice(templates)
    s = random.choice(subjects)
    loc = random.choice(locations)

    if "{veh}" in t:
        txt = t.format(s=s, veh=random.choice(vehicles), loc=loc)
    elif "{npc}" in t:
        txt = t.format(s=s, npc=random.choice(npcs), loc=loc)
    elif "{items}" in t:
        txt = t.format(s=s, items=random.choice(items_plural), loc=loc)
    else:
        txt = t.format(s=s, prop=random.choice(props), loc=loc)

    return _sanitize(txt)

# ========= ХЭНДЛЕРЫ =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    users[uid].update({
        "mode": None, "source_text": None, "scene": None, "style": None, "replica": None,
        "awaiting_scene": False, "awaiting_custom_style": False
    })
    await update.message.reply_text("Привет! Выбирай режим 👇", reply_markup=kb_home())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _ensure(uid)
    st = users[uid]
    text = _sanitize((update.message.text or "").strip())

    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"✅ Выбран стиль: **{st['style']}**")
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
            
        if st["mode"] == "nkudo" and gpt:
            scene, replica = nkudo_scene(text)
            st["scene"], st["replica"] = scene, replica
            msg = f"🧪 Сцена в стиле NEUROKUDO:\n\n{scene}"
            if replica:
                msg += f"\n\n💬 Реплика: {replica}"
            await update.message.reply_text(msg, reply_markup=kb_variants_nkudo())
            return
            
        # manual
        st["scene"] = text
        await update.message.reply_text(f"📝 Промт принят:\n\n{text}", reply_markup=kb_variants())
        return

    # Вне контекста – вернуть меню
    await update.message.reply_text("Главное меню:", reply_markup=kb_home())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    _ensure(uid)
    st = users[uid]
    data = q.data
    log.info("Button: %s", data)

    # --- Главное меню
    if data == "menu_make":
        await q.message.edit_text("Выберите режим генерации:", reply_markup=kb_modes())
        return
    if data == "menu_alive":
        await q.message.edit_text("🖼️ Оживление изображения: пришлите фото и короткий промт (в разработке).")
        return
    if data == "menu_guides":
        await q.message.edit_text("📚 Гайды и оплата — скоро тут ❤️")
        return
    if data == "menu_profile":
        await q.message.edit_text("💤 Профиль/Баланс — скоро доступно.")
        return
    if data == "back_home":
        await q.message.edit_text("Главное меню:", reply_markup=kb_home())
        return

    # --- Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.edit_text("🧠✨ Режим умного помощника активирован!")
        await q.message.reply_text("Опиши сцену — сделаю её съёмочной на ~8 секунд.")
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
        st["awaiting_scene"] = True
        await q.message.edit_text("🧪 Включён режим «Как у NEUROKUDO»!")
        await q.message.reply_text("Опиши черновик сцены — соберу фирменный вариант.")
        return

    # --- Варианты сцены
    if data in ("var_complex", "var_simple", "var_absurd", "var_again"):
        scene = st.get("scene")
        if not scene:
            await q.message.reply_text("Сначала опиши сцену."); return
            
        title = "Новый вариант"
        
        if st.get("mode") == "nkudo":
            # В NEUROKUDO режиме абсурд и упрощение
            if data == "var_absurd":
                st["scene"] = nkudo_refine(scene, "absurd")
                title = "Вариант (абсурднее)"
            elif data == "var_simple":
                st["scene"] = nkudo_refine(scene, "simple")
                title = "Вариант (проще)"
            else:
                base = st.get("source_text") or scene
                st["scene"], _ = nkudo_scene(base)
            await q.message.edit_text(f"✏️ {title}:\n\n{st['scene']}", reply_markup=kb_variants_nkudo())
        elif st.get("mode") == "meme":
            # В мемном режиме - только абсурд доступен из мемного меню
            if data == "var_again":
                st["scene"] = random_meme_scene()
                title = "Новая мемная сцена"
            await q.message.edit_text(f"🎲 {title}:\n\n{st['scene']}", reply_markup=kb_meme())
        else:
            # В обычных режимах (helper, manual) - усложнение/упрощение
            if data == "var_complex":
                st["scene"] = improve_scene(scene, mode="complex")
                title = "Вариант (усложнённый)"
            elif data == "var_simple":
                st["scene"] = improve_scene(scene, mode="simple")
                title = "Вариант (упрощённый)"
            else:
                base = st.get("source_text") or scene
                st["scene"] = improve_scene(base, mode="normal")
            await q.message.edit_text(f"✏️ {title}:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Мемный режим кнопки
    if data == "meme_again":
        st["scene"] = random_meme_scene()
        await q.message.edit_text(f"🎭 Мемная сцена:\n\n{st['scene']}", reply_markup=kb_meme())
        return
    if data == "meme_to_helper":
        st["scene"] = improve_scene(st.get("scene", ""), mode="normal")
        st["mode"] = "helper"
        await q.message.edit_text(f"🧠✨ Улучшено помощником:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Переход на следующий шаг (выбор стиля)
    if data in ("go_next", "choose_style"):
        # Сохраняем финальную сцену в сообщении
        if st.get("scene"):
            await q.message.edit_text(f"✅ Сцена готова:\n\n{st['scene']}")
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles())
        return

    # --- Стили
    if data.startswith("style_"):
        val = data.split("_", 1)[1]
        if val == "custom":
            st["awaiting_custom_style"] = True
            await q.message.edit_text("✏️ Напишите желаемый стиль для видео:")
            return
        st["style"] = None if val == "None" else val
        style_text = st['style'] or "Без стиля"
        await q.message.edit_text(f"✅ Выбран стиль: **{style_text}**")
        await q.message.reply_text("Что делаем дальше?", reply_markup=kb_after_style())
        return

    # --- Реплика
    if data == "add_replica":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("mode") == "nkudo":
            text = nkudo_replica(st["scene"])
        else:
            text = suggest_replica(st["scene"]) or "Поехали уже!"
        st["replica"] = text
        await q.message.edit_text(f"✅ Создана реплика: **{text}**")
        await q.message.reply_text("Готово! Давайте посмотрим итоговый промпт.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 Посмотреть промпт", callback_data="show_final")]
        ]))
        return

    # --- Показ финального промпта
    if data == "show_final":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        
        final_text = f"📝 **Итоговый промпт:**\n\n"
        final_text += f"🎬 **Сцена:** {st['scene']}\n\n"
        
        if st.get("style"):
            final_text += f"🎨 **Стиль:** {st['style']}\n\n"
        
        if st.get("replica"):
            final_text += f"💬 **Реплика:** {st['replica']}\n\n"
        
        final_text += "Всё готово для генерации!"
        
        await q.message.reply_text(final_text, reply_markup=kb_final_prompt())
        return

    # --- Генерация видео (Veo)
    if data == "generate_now":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None:
            st["style"] = DEFAULT_STYLE

        # Удаляем кнопки из предыдущего сообщения
        try:
            await q.message.edit_reply_markup(reply_markup=None)
        except:
            pass
            
        msg = await q.message.reply_text("⏳ Генерирую видео… Это может занять несколько минут.")
        try:
            mp4_path = await asyncio.to_thread(
                generate_video_sync, st["scene"], st["style"], st.get("replica"), 8
            )
            caption = (
                f"✅ Видео готово!\n\n"
                f"🎬 Сцена: {st['scene']}\n"
                f"🎨 Стиль: {st['style']}"
                + (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "")
            )
            with open(mp4_path, "rb") as f:
                await q.message.reply_video(video=f, caption=caption, supports_streaming=True)
            
            # После успешной генерации предлагаем создать новое видео
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
