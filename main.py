# main.py — Бабка Бот (GPT + Veo)
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

# ------------------ ENV / LOG ------------------
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("babka-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_STYLE = "Кино"

# ------------------ OpenAI (GPT) ------------------
from openai import OpenAI
gpt: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        gpt = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI GPT активирован.")
    except Exception as e:
        log.error("OpenAI init error: %s", e)

def _sanitize(text: str) -> str:
    if not text:
        return text
    # убрать кавычки и тире всех видов (для озвучки)
    bad = ['"', '«', '»', '„', '“', '‟', '‹', '›', "'", '’', '‚', '‛', '‐', '-', '‒', '–', '—', '―']
    for ch in bad:
        text = text.replace(ch, "")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()

def _gpt(system: str, user: str, temperature=0.7, max_tokens=220) -> Optional[str]:
    if not gpt:
        return None
    try:
        r = gpt.chat.completions.create(
            model="gpt-4o-mini",
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

SMALLTALK = {"привет", "здарова", "как дела", "погода", "кто ты", "анекдот", "что умеешь", "расскажи"}
def _looks_like_scene(txt: str) -> bool:
    t = txt.lower().strip()
    if t in SMALLTALK:
        return False
    # минимум 2 слова и > 12 символов — примитивная эвристика «это сцена, а не болтовня»
    return len(t) >= 12 and (" " in t)

# ---- Улучшаем сцену (8 сек, ≤2 плана, без лирики) ----
def improve_scene(user_text: str, mode: str = "normal") -> str:
    style = {
        "normal": "Сделай рабочую сцену.",
        "absurd": "Сделай сцену более абсурдной и смешной.",
        "simple": "Сделай сцену проще и короче.",
    }.get(mode, "Сделай рабочую сцену.")
    sys = (
        "Ты редактор коротких видеосцен. "
        "Формулируй именно СЦЕНУ: кто где что делает. "
        "Длительность примерно 8 секунд, максимум две смены плана. "
        "Только действие и читаемые визуальные детали, без поэтических эмо-описаний. "
        "Запрещены субтитры/логотипы/текст в кадре. "
        "СТРОГО не используй кавычки и тире. "
        f"{style} Напиши 1–2 коротких предложения."
    )
    out = _gpt(sys, user_text, temperature=0.65 if mode != "absurd" else 0.9, max_tokens=140)
    return out or _sanitize(user_text)

def suggest_replica(scene: str) -> Optional[str]:
    sys = "Придумай короткую реплику героя к сцене, 4–10 слов. Только сама фраза. Без кавычек и тире."
    return _gpt(sys, scene, temperature=0.9, max_tokens=35)

# ------------------ NEUROKUDO ------------------
NKUDO_SYSTEM = (
    "Ты редактор видеосцен в фирменном стиле NEUROKUDO. "
    "Пиши сухо и конкретно. 8 секунд экранного времени, максимум два плана. "
    "Обязательные приёмы: 1) переворот ожиданий; 2) контраст официоза и народной речи; "
    "3) лёгкая эскалация абсурда при правдоподобии; 4) фоновая немая шутка в кадре; "
    "5) финальная короткая ласково грубая реплика бабки. "
    "Никаких кавычек и тире, никаких титров или текста в кадре."
)

def nkudo_scene(seed: str) -> tuple[str, Optional[str]]:
    usr = (
        seed.strip() + "\n\n"
        "Дай:\n"
        "A) СЦЕНА — 3–5 коротких предложений действий и кадра. "
        "Отметь где план 1 и где план 2 если он есть. Без эмо-литературы.\n"
        "B) РЕПЛИКА — одна короткая фраза персонажа в конце, без кавычек и тире."
    )
    resp = _gpt(NKUDO_SYSTEM, usr, temperature=0.55, max_tokens=260) or seed
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

# ------------------ VEO (генерация видео) ------------------
# должен возвращать путь до mp4
from veo_client import generate_video_sync

# ------------------ STATE ------------------
State = Dict[str, Any]
users: Dict[int, State] = {}

def _ensure(uid: int):
    if uid not in users:
        users[uid] = {
            "mode": None,
            "source_text": None,   # исходник пользователя (если есть)
            "scene": None,
            "style": None,
            "replica": None,
            "awaiting_scene": False,
            "awaiting_custom_style": False,
            "history": [],         # простая история сцен
        }

# ------------------ KEYBOARDS ------------------
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
        [InlineKeyboardButton("🧪 Как у NEUROKUDO", callback_data="mode_nkudo")],
        [InlineKeyboardButton("✍️ Я сам напишу промт", callback_data="mode_manual")],
        [InlineKeyboardButton("🎲 Мемный режим", callback_data="mode_meme")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_ask_scene():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖💡 Помощник, предложи своё", callback_data="pitch_idea")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_home")],
    ])

def kb_nkudo_intro():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Создать как у NEUROKUDO", callback_data="nkudo_create")],
        [InlineKeyboardButton("⬅️ Назад к режимам", callback_data="menu_make")],
    ])

def kb_variants():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤪 Абсурднее", callback_data="var_absurd"),
         InlineKeyboardButton("🎯 Проще", callback_data="var_simple")],
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
        [InlineKeyboardButton("🚀 Без стиля — генерировать", callback_data="style_None")],
    ])

def kb_after_style():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Придумать реплику", callback_data="add_replica")],
        [InlineKeyboardButton("🚀 Сгенерировать сейчас", callback_data="generate_now")],
    ])

def kb_meme():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Крутить ещё", callback_data="meme_again")],
        [InlineKeyboardButton("🧠✨ Улучшить с помощником", callback_data="meme_to_helper")],
        [InlineKeyboardButton("➡️ Дальше", callback_data="go_next")],
    ])

# ------------------ MEME MODE ------------------
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

# ------------------ HANDLERS ------------------
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

    # если пользователь находится в NKUDO-экране (ввод текста не нужен) — игнорим и показываем кнопку
    if st.get("mode") == "nkudo" and not st.get("awaiting_scene"):
        await update.message.reply_text("В этом разделе сцены создаются по кнопке ниже:", reply_markup=kb_nkudo_intro())
        return

    # кастомный стиль
    if st["awaiting_custom_style"]:
        st["awaiting_custom_style"] = False
        st["style"] = text
        await update.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
        await update.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())
        return

    # ждём сцену (helper/manual)
    if st["awaiting_scene"]:
        t = text.lower()
        if t in {"предложи свое", "предложи своё", "дай идею", "предложи"}:
            await _pitch_idea(update.message, st)
            return
        if not _looks_like_scene(text):
            await update.message.reply_text(
                "Нужна короткая сцена на ~8 секунд: кто где что делает (1–2 предложения). "
                "Или жми «🤖💡 Помощник, предложи своё».",
                reply_markup=kb_ask_scene()
            )
            return

        st["source_text"] = text
        if st["mode"] == "helper" and gpt:
            scene = improve_scene(text, mode="normal")
            st["scene"] = scene
            await update.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{scene}", reply_markup=kb_variants())
            return
        # manual
        st["scene"] = text
        await update.message.reply_text(f"📝 Промт принят:\n\n{text}", reply_markup=kb_variants())
        return

    # всё остальное — главное меню (GPT не зовём)
    await update.message.reply_text("Главное меню:", reply_markup=kb_home())

async def _pitch_idea(message, st):
    if st.get("mode") == "nkudo" and gpt:
        scene, replica = nkudo_scene(
            "Предложи оригинальную бытовую сцену на 8 секунд. Макс два плана. "
            "Только действия и визуальные детали. Без кавычек и тире. Без текста/логотипов в кадре."
        )
        st["scene"], st["replica"] = scene, replica
        txt = f"🧪 Сцена в стиле NEUROKUDO:\n\n{scene}"
        if replica:
            txt += f"\n\n💬 Реплика: {replica}"
        await message.reply_text(txt, reply_markup=kb_variants())
    else:
        seed = ("Придумай короткую сцену на 8 секунд. Макс два плана. "
                "Только действие, без лишних эмо-описаний. Без кавычек и тире.")
        st["scene"] = improve_scene(seed, mode="normal")
        await message.reply_text(f"🧠✨ Предложено помощником:\n\n{st['scene']}", reply_markup=kb_variants())
    st["awaiting_scene"] = False

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
        await q.message.reply_text("Выберите режим генерации:", reply_markup=kb_modes()); return
    if data == "menu_alive":
        await q.message.reply_text("🖼️ Оживление изображения: пришлите фото и короткий промт (в разработке)."); return
    if data == "menu_guides":
        await q.message.reply_text("📚 Гайды и оплата — скоро тут ❤️"); return
    if data == "menu_profile":
        await q.message.reply_text("👤 Профиль/Баланс — скоро доступно."); return
    if data == "back_home":
        await q.message.reply_text("Главное меню:", reply_markup=kb_home()); return

    # --- Режимы
    if data == "mode_helper":
        st.update({"mode": "helper", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.reply_text(
            "🧠✨ Опиши сцену — сделаю её съёмочной на ~8 секунд. "
            "Или нажми «🤖💡 Помощник, предложи своё».",
            reply_markup=kb_ask_scene()
        )
        return

    if data == "mode_manual":
        st.update({"mode": "manual", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = True
        await q.message.reply_text("✍️ Введи свою сцену (я ничего не меняю).")
        return

    if data == "mode_meme":
        st.update({"mode": "meme", "style": None, "replica": None})
        st["scene"] = random_meme_scene()
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{st['scene']}", reply_markup=kb_meme())
        return

    if data == "mode_nkudo":
        st.update({"mode": "nkudo", "scene": None, "style": None, "replica": None})
        st["awaiting_scene"] = False  # текст не ждём
        await q.message.reply_text(
            "🧪 Режим «Как у NEUROKUDO».\n\n"
            "Собираю сцены в фирменной логике: 8 секунд, максимум два плана, "
            "переворот ожиданий, контраст официоза и народной речи, фоновая немая шутка, "
            "в финале короткая ласково грубая реплика. Без кавычек и тире, без текста в кадре.\n\n"
            "Нажми кнопку ниже:",
            reply_markup=kb_nkudo_intro()
        )
        return

    if data == "nkudo_create":
        scene, replica = nkudo_scene(
            "Предложи оригинальную бытовую сцену на 8 секунд. Макс два плана. "
            "Только действия и визуальные детали. Без кавычек и тире. Без текста/логотипов в кадре."
        )
        st["scene"], st["replica"] = scene, replica
        txt = f"🧪 Сцена в стиле NEUROKUDO:\n\n{scene}"
        if replica:
            txt += f"\n\n💬 Реплика: {replica}"
        await q.message.reply_text(txt, reply_markup=kb_variants())
        return

    # --- Просьба «предложи своё»
    if data == "pitch_idea":
        await _pitch_idea(q.message, st); return

    # --- Варианты сцены
    if data in ("var_absurd", "var_simple", "var_again"):
        scene = st.get("scene")
        if not scene:
            await q.message.reply_text("Сначала опиши сцену."); return
        title = "Новый вариант"
        if st.get("mode") == "nkudo":
            if data == "var_absurd":
                st["scene"] = nkudo_refine(scene, "absurd"); title = "Вариант (абсурднее)"
            elif data == "var_simple":
                st["scene"] = nkudo_refine(scene, "simple"); title = "Вариант (проще)"
            else:
                st["scene"], _ = nkudo_scene(
                    "Дай новую оригинальную фирменную сцену на 8 секунд, макс два плана. Без кавычек и тире."
                )
        else:
            if data == "var_absurd":
                st["scene"] = improve_scene(scene, mode="absurd"); title = "Вариант (абсурднее)"
            elif data == "var_simple":
                st["scene"] = improve_scene(scene, mode="simple"); title = "Вариант (проще)"
            else:
                base = st.get("source_text") or scene
                st["scene"] = improve_scene(base, mode="normal")
        await q.message.reply_text(f"✏️ {title}:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Мемный режим кнопки
    if data == "meme_again":
        st["scene"] = random_meme_scene()
        await q.message.reply_text(f"🎭 Мемная сцена:\n\n{st['scene']}", reply_markup=kb_meme())
        return
    if data == "meme_to_helper":
        st["scene"] = improve_scene(st.get("scene", ""), mode="normal")
        st["mode"] = "helper"
        await q.message.reply_text(f"🧠✨ Улучшено помощником:\n\n{st['scene']}", reply_markup=kb_variants())
        return

    # --- Переход к стилям
    if data in ("go_next", "choose_style"):
        await q.message.reply_text("Выбери стиль:", reply_markup=kb_styles()); return

    # --- Стили
    if data.startswith("style_"):
        val = data.split("_", 1)[1]
        st["style"] = None if val == "None" else val
        await q.message.reply_text(f"🎨 Стиль выбран: {st['style']}")
        await q.message.reply_text("Теперь можно добавить реплику или сразу сгенерировать.", reply_markup=kb_after_style())
        return
    if data == "style_custom":
        st["awaiting_custom_style"] = True
        await q.message.reply_text("Введи свой стиль текстом:"); return

    # --- Реплика
    if data == "add_replica":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("mode") == "nkudo":
            text = nkudo_replica(st["scene"])
        else:
            text = suggest_replica(st["scene"]) or "Поехали уже!"
        st["replica"] = text
        await q.message.reply_text(f"💬 Реплика предложена: {text}")
        await q.message.reply_text("Готово! Можно генерировать.", reply_markup=kb_after_style())
        return

    # --- Генерация (Veo)
    if data == "generate_now":
        if not st.get("scene"):
            await q.message.reply_text("Сначала опиши сцену."); return
        if st.get("style") is None:
            st["style"] = DEFAULT_STYLE
        msg = await q.message.reply_text("⏳ Генерирую видео…")
        try:
            mp4_path = await asyncio.to_thread(
                generate_video_sync, st["scene"], st["style"], st.get("replica"), 8
            )
            caption = f"✅ Готово!\n\n📝 Сцена: {st['scene']}\n🎨 Стиль: {st['style']}" + \
                      (f"\n💬 Реплика: {st['replica']}" if st.get("replica") else "")
            with open(mp4_path, "rb") as f:
                await q.message.reply_video(video=f, caption=caption, supports_streaming=True)
            # история
            users[uid]["history"].append({"scene": st["scene"], "style": st["style"], "replica": st.get("replica")})
        except Exception as e:
            log.exception("Veo generation failed")
            await q.message.reply_text(f"❌ Ошибка генерации: {e}")
        finally:
            try:
                await msg.delete()
            except Exception:
                pass
        return

    # fallback
    await q.message.reply_text("Команда пока не поддерживается. Возврат в меню.", reply_markup=kb_home())

# ------------------ RUN ------------------
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

