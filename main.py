"""
Babka Bot - Telegram бот для генерации контента с AI
Минимально рабочая версия с новой архитектурой
"""

import os
import asyncio
import logging
from typing import Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# Импорты из новой архитектуры
from app.utils.logging import setup_logging
from app.services.pricing import coins_for_tariff, price_rub_for_tariff, feature_cost_coins
from app.services.wallet import WalletService
from app.db.queries import db_manager

# Настройка логирования
logger = setup_logging()
log = logging.getLogger("babka_bot")

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не найден в переменных окружения")

# Глобальное хранилище пользователей (временное решение)
user_wallets = {}

def get_user_wallet(user_id: int) -> WalletService:
    """Получить или создать кошелек пользователя"""
    if user_id not in user_wallets:
        # Получаем пользователя из БД или создаем нового
        user = db_manager.get_user(user_id)
        if not user:
            # Создаем нового пользователя с базовым балансом
            user = db_manager.create_user(user_id)
            # Даем стартовые монеты
            db_manager.update_user_balance(user_id, 50)
        
        user_wallets[user_id] = WalletService(user_id, user.balance)
    
    return user_wallets[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Получаем кошелек пользователя
    wallet = get_user_wallet(user_id)
    balance = wallet.get_balance()
    
    welcome_text = f"""
🎉 Добро пожаловать в Babka Bot, {user.first_name}!

🤖 Я помогу вам создавать:
• 🎬 Видео с помощью AI (Veo)
• 🖼️ Изображения и виртуальную примерочную
• ✨ Обработку фото (удаление фона, ретушь и др.)

💰 Ваш баланс: {balance} монет

Выберите действие:
"""
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("🎬 Генерация видео", callback_data="video_menu")],
        [InlineKeyboardButton("🖼️ Изображения", callback_data="image_menu")],
        [InlineKeyboardButton("👗 Виртуальная примерочная", callback_data="tryon_menu")],
        [InlineKeyboardButton("💰 Баланс и тарифы", callback_data="balance_menu")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    wallet = get_user_wallet(user_id)
    
    if query.data == "video_menu":
        await show_video_menu(query)
    elif query.data == "image_menu":
        await show_image_menu(query)
    elif query.data == "tryon_menu":
        await show_tryon_menu(query)
    elif query.data == "balance_menu":
        await show_balance_menu(query)
    elif query.data == "help_menu":
        await show_help_menu(query)
    elif query.data.startswith("video_"):
        await handle_video_action(query, wallet)
    elif query.data.startswith("image_"):
        await handle_image_action(query, wallet)
    elif query.data.startswith("tryon_"):
        await handle_tryon_action(query, wallet)
    elif query.data.startswith("tariff_"):
        await handle_tariff_action(query, wallet)

async def show_video_menu(query):
    """Показать меню генерации видео"""
    text = """
🎬 Генерация видео

Выберите тип видео:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎬 Видео с аудио (20 монет)", callback_data="video_8s_audio")],
        [InlineKeyboardButton("🔇 Видео без аудио (16 монет)", callback_data="video_8s_mute")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_image_menu(query):
    """Показать меню изображений"""
    text = """
🖼️ Обработка изображений

Выберите тип обработки:
"""
    
    keyboard = [
        [InlineKeyboardButton("🖼️ Базовая обработка (1 монета)", callback_data="image_basic")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_tryon_menu(query):
    """Показать меню виртуальной примерочной"""
    text = """
👗 Виртуальная примерочная

Попробуйте надеть одежду на фото!
"""
    
    keyboard = [
        [InlineKeyboardButton("👗 Виртуальная примерочная (3 монеты)", callback_data="virtual_tryon")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_balance_menu(query):
    """Показать меню баланса и тарифов"""
    user_id = query.from_user.id
    wallet = get_user_wallet(user_id)
    balance = wallet.get_balance()
    
    text = f"""
💰 Баланс и тарифы

Ваш баланс: {balance} монет

Доступные тарифы:
• Lite: {price_rub_for_tariff("lite")}₽ → {coins_for_tariff("lite")} монет
• Standard: {price_rub_for_tariff("standard")}₽ → {coins_for_tariff("standard")} монет  
• Pro: {price_rub_for_tariff("pro")}₽ → {coins_for_tariff("pro")} монет
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Lite тариф", callback_data="tariff_lite")],
        [InlineKeyboardButton("💳 Standard тариф", callback_data="tariff_standard")],
        [InlineKeyboardButton("💳 Pro тариф", callback_data="tariff_pro")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_help_menu(query):
    """Показать меню помощи"""
    text = """
ℹ️ Помощь

🤖 Babka Bot - это AI-бот для создания контента:

🎬 Генерация видео:
• Отправьте текстовое описание видео
• Выберите с аудио или без
• Получите готовое видео

🖼️ Обработка изображений:
• Загрузите фото
• Выберите тип обработки
• Получите результат

👗 Виртуальная примерочная:
• Загрузите фото человека и одежды
• Получите результат примерки

💰 Монеты используются для оплаты функций.
Пополняйте баланс через тарифы.
"""
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_video_action(query, wallet: WalletService):
    """Обработка действий с видео"""
    feature_key = query.data
    
    if not wallet.can_afford(feature_key):
        cost = wallet.get_cost(feature_key)
        balance = wallet.get_balance()
        text = f"""
❌ Недостаточно монет!

Нужно: {cost} монет
У вас: {balance} монет

Пополните баланс в разделе "💰 Баланс и тарифы"
"""
        keyboard = [[InlineKeyboardButton("💰 Пополнить баланс", callback_data="balance_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # Тратим монеты
    if wallet.spend_coins(feature_key):
        # Обновляем баланс в БД
        db_manager.spend_coins(query.from_user.id, wallet.get_cost(feature_key), feature_key)
        
        text = f"""
✅ Монеты списаны!

Остаток: {wallet.get_balance()} монет

Отправьте текстовое описание видео для генерации.
"""
        await query.edit_message_text(text)
    else:
        await query.edit_message_text("❌ Ошибка при списании монет")

async def handle_image_action(query, wallet: WalletService):
    """Обработка действий с изображениями"""
    feature_key = query.data
    
    if not wallet.can_afford(feature_key):
        cost = wallet.get_cost(feature_key)
        balance = wallet.get_balance()
        text = f"""
❌ Недостаточно монет!

Нужно: {cost} монет
У вас: {balance} монет

Пополните баланс в разделе "💰 Баланс и тарифы"
"""
        keyboard = [[InlineKeyboardButton("💰 Пополнить баланс", callback_data="balance_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # Тратим монеты
    if wallet.spend_coins(feature_key):
        # Обновляем баланс в БД
        db_manager.spend_coins(query.from_user.id, wallet.get_cost(feature_key), feature_key)
        
        text = f"""
✅ Монеты списаны!

Остаток: {wallet.get_balance()} монет

Загрузите изображение для обработки.
"""
        await query.edit_message_text(text)
    else:
        await query.edit_message_text("❌ Ошибка при списании монет")

async def handle_tryon_action(query, wallet: WalletService):
    """Обработка действий с виртуальной примерочной"""
    feature_key = query.data
    
    if not wallet.can_afford(feature_key):
        cost = wallet.get_cost(feature_key)
        balance = wallet.get_balance()
        text = f"""
❌ Недостаточно монет!

Нужно: {cost} монет
У вас: {balance} монет

Пополните баланс в разделе "💰 Баланс и тарифы"
"""
        keyboard = [[InlineKeyboardButton("💰 Пополнить баланс", callback_data="balance_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # Тратим монеты
    if wallet.spend_coins(feature_key):
        # Обновляем баланс в БД
        db_manager.spend_coins(query.from_user.id, wallet.get_cost(feature_key), feature_key)
        
        text = f"""
✅ Монеты списаны!

Остаток: {wallet.get_balance()} монет

Загрузите фото человека и одежды для виртуальной примерки.
"""
        await query.edit_message_text(text)
    else:
        await query.edit_message_text("❌ Ошибка при списании монет")

async def handle_tariff_action(query, wallet: WalletService):
    """Обработка покупки тарифов"""
    tariff_name = query.data.replace("tariff_", "")
    
    # Здесь должна быть интеграция с платежной системой
    # Пока просто показываем информацию
    price = price_rub_for_tariff(tariff_name)
    coins = coins_for_tariff(tariff_name)
    
    text = f"""
💳 Тариф {tariff_name.title()}

Цена: {price}₽
Монеты: {coins}

⚠️ Покупка тарифов временно недоступна.
Для тестирования используйте команду /add_coins [количество]
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="balance_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def add_coins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления монет (для тестирования)"""
    user_id = update.effective_user.id
    
    # Проверяем, что это админ (заглушка для тестирования)
    if user_id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    try:
        amount = int(context.args[0]) if context.args else 100
        wallet = get_user_wallet(user_id)
        wallet.add_coins(amount)
        
        # Обновляем баланс в БД
        db_manager.update_user_balance(user_id, amount)
        db_manager.add_transaction(user_id, "purchase", amount, description="Test coins")
        
        await update.message.reply_text(f"✅ Добавлено {amount} монет. Баланс: {wallet.get_balance()}")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /add_coins [количество]")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text and not text.startswith('/'):
        # Здесь будет обработка текстовых запросов для генерации
        await update.message.reply_text("📝 Ваш запрос принят! Функции генерации будут добавлены в следующих версиях.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загруженных фото"""
    user_id = update.effective_user.id
    
    # Здесь будет обработка загруженных изображений
    await update.message.reply_text("📸 Фото получено! Функции обработки изображений будут добавлены в следующих версиях.")

async def main():
    """Главная функция запуска бота"""
    log.info("Запуск Babka Bot...")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_coins", add_coins_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Запускаем бота
    log.info("Бот запущен и готов к работе!")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен пользователем")
    except Exception as e:
        log.error(f"Ошибка при запуске бота: {e}")
        raise