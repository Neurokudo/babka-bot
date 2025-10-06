"""
Админские команды для управления балансом и аудитом
"""

from aiogram import types, Router
from aiogram.filters import Command
from app.services import balance_manager, billing_observer
from app.config.pricing import FEATURE_DESCRIPTIONS
import logging
from typing import Optional

log = logging.getLogger("babka-bot")
admin_router = Router()

# Список админов (можно вынести в конфиг)
ADMIN_IDS = [5015100177]  # Добавьте сюда ID администраторов

def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

@admin_router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Показать баланс пользователя и последние транзакции"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы команды
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Использование: /balance <user_id>")
            return
        
        user_id = int(args[1])
        summary = balance_manager.get_user_summary(user_id)
        
        # Форматируем ответ
        response = f"💰 <b>Баланс пользователя {user_id}</b>\n\n"
        response += f"💎 Текущий баланс: <b>{summary['current_balance']}</b> монет\n\n"
        
        if summary['recent_transactions']:
            response += "📋 <b>Последние транзакции:</b>\n"
            for tx in summary['recent_transactions'][:5]:
                delta_str = f"+{tx['delta']}" if tx['delta'] > 0 else str(tx['delta'])
                feature_desc = FEATURE_DESCRIPTIONS.get(tx['feature'], tx['feature'])
                response += f"• {delta_str} монет | {feature_desc} | {tx['reason']}\n"
        else:
            response += "📋 Нет транзакций"
        
        await message.reply(response, parse_mode="HTML")
        
    except ValueError:
        await message.reply("❌ Неверный формат user_id")
    except Exception as e:
        log.error(f"Error in /balance command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("set_balance"))
async def cmd_set_balance(message: types.Message):
    """Установить баланс пользователя"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы: /set_balance <user_id> <new_balance> [reason]
        args = message.text.split()
        if len(args) < 3:
            await message.reply("❌ Использование: /set_balance <user_id> <new_balance> [reason]")
            return
        
        user_id = int(args[1])
        new_balance = int(args[2])
        reason = " ".join(args[3:]) if len(args) > 3 else "Admin set balance"
        
        old_balance = balance_manager.get_balance(user_id)
        balance_manager.set_balance(
            user_id=user_id,
            new_balance=new_balance,
            reason=reason,
            admin_note=f"Admin {message.from_user.id}"
        )
        
        response = f"✅ <b>Баланс обновлен</b>\n\n"
        response += f"👤 Пользователь: {user_id}\n"
        response += f"💰 Было: {old_balance} монет\n"
        response += f"💰 Стало: {new_balance} монет\n"
        response += f"📝 Причина: {reason}"
        
        await message.reply(response, parse_mode="HTML")
        
    except ValueError as e:
        await message.reply(f"❌ Неверный формат: {e}")
    except Exception as e:
        log.error(f"Error in /set_balance command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("billing_report"))
async def cmd_billing_report(message: types.Message):
    """Показать отчет по биллингу"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы: /billing_report [daily|weekly|monthly]
        args = message.text.split()
        period = args[1] if len(args) > 1 else "daily"
        
        if period == "daily":
            report = billing_observer.get_daily_report()
        elif period == "weekly":
            report = billing_observer.get_weekly_report()
        elif period == "monthly":
            report = billing_observer.get_monthly_report()
        else:
            await message.reply("❌ Доступные периоды: daily, weekly, monthly")
            return
        
        response = billing_observer.format_report(report)
        await message.reply(response)
        
    except Exception as e:
        log.error(f"Error in /billing_report command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("audit"))
async def cmd_audit(message: types.Message):
    """Показать детальную историю пользователя"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы: /audit <user_id> [limit]
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Использование: /audit <user_id> [limit]")
            return
        
        user_id = int(args[1])
        limit = int(args[2]) if len(args) > 2 else 20
        
        transactions = billing_observer.get_user_recent_transactions(user_id, limit)
        
        response = f"📊 <b>Аудит пользователя {user_id}</b>\n\n"
        
        if transactions:
            for tx in transactions:
                delta_str = f"+{tx['delta']}" if tx['delta'] > 0 else str(tx['delta'])
                feature_desc = FEATURE_DESCRIPTIONS.get(tx['feature'], tx['feature'])
                timestamp = tx['timestamp'].strftime("%Y-%m-%d %H:%M")
                response += f"• {delta_str} | {feature_desc} | {tx['reason']} | {timestamp}\n"
        else:
            response += "📋 Нет транзакций"
        
        await message.reply(response, parse_mode="HTML")
        
    except ValueError as e:
        await message.reply(f"❌ Неверный формат: {e}")
    except Exception as e:
        log.error(f"Error in /audit command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("add_coins"))
async def cmd_add_coins(message: types.Message):
    """Добавить монеты пользователю"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы: /add_coins <user_id> <amount> <reason>
        args = message.text.split()
        if len(args) < 4:
            await message.reply("❌ Использование: /add_coins <user_id> <amount> <reason>")
            return
        
        user_id = int(args[1])
        amount = int(args[2])
        reason = " ".join(args[3:])
        
        new_balance = balance_manager.add_coins(
            user_id=user_id,
            amount=amount,
            reason=reason,
            feature="manual_add"
        )
        
        response = f"✅ <b>Монеты добавлены</b>\n\n"
        response += f"👤 Пользователь: {user_id}\n"
        response += f"💰 Добавлено: +{amount} монет\n"
        response += f"💰 Новый баланс: {new_balance} монет\n"
        response += f"📝 Причина: {reason}"
        
        await message.reply(response, parse_mode="HTML")
        
    except ValueError as e:
        await message.reply(f"❌ Неверный формат: {e}")
    except Exception as e:
        log.error(f"Error in /add_coins command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("spend_coins"))
async def cmd_spend_coins(message: types.Message):
    """Списать монеты у пользователя"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    try:
        # Парсим аргументы: /spend_coins <user_id> <amount> <reason>
        args = message.text.split()
        if len(args) < 4:
            await message.reply("❌ Использование: /spend_coins <user_id> <amount> <reason>")
            return
        
        user_id = int(args[1])
        amount = int(args[2])
        reason = " ".join(args[3:])
        
        new_balance = balance_manager.spend_coins(
            user_id=user_id,
            amount=amount,
            reason=reason,
            feature="manual_spend"
        )
        
        response = f"✅ <b>Монеты списаны</b>\n\n"
        response += f"👤 Пользователь: {user_id}\n"
        response += f"💰 Списано: -{amount} монет\n"
        response += f"💰 Новый баланс: {new_balance} монет\n"
        response += f"📝 Причина: {reason}"
        
        await message.reply(response, parse_mode="HTML")
        
    except balance_manager.InsufficientFundsError:
        await message.reply("❌ Недостаточно средств у пользователя")
    except ValueError as e:
        await message.reply(f"❌ Неверный формат: {e}")
    except Exception as e:
        log.error(f"Error in /spend_coins command: {e}")
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("help_admin"))
async def cmd_help_admin(message: types.Message):
    """Показать справку по админским командам"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора")
        return
    
    help_text = """
🔧 <b>Админские команды</b>

💰 <b>Управление балансом:</b>
/balance &lt;user_id&gt; - показать баланс и транзакции
/set_balance &lt;user_id&gt; &lt;new_balance&gt; [reason] - установить баланс
/add_coins &lt;user_id&gt; &lt;amount&gt; &lt;reason&gt; - добавить монеты
/spend_coins &lt;user_id&gt; &lt;amount&gt; &lt;reason&gt; - списать монеты

📊 <b>Отчеты и аудит:</b>
/billing_report [daily|weekly|monthly] - отчет по биллингу
/audit &lt;user_id&gt; [limit] - детальная история пользователя

❓ <b>Справка:</b>
/help_admin - эта справка
"""
    
    await message.reply(help_text, parse_mode="HTML")
