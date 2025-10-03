from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from app.services.pricing import feature_cost_coins, get_available_tariffs, get_available_topup_packs

class WalletService:
    """Сервис для работы с кошельком пользователя"""
    
    def __init__(self, user_id: int, initial_balance: int = 0):
        self.user_id = user_id
        self.balance = initial_balance
    
    def get_balance(self) -> int:
        """Получить текущий баланс в монетах"""
        return self.balance
    
    def add_coins(self, amount: int) -> bool:
        """Добавить монеты к балансу"""
        if amount <= 0:
            return False
        self.balance += amount
        return True
    
    def spend_coins(self, feature_key: str) -> bool:
        """Потратить монеты на функцию"""
        cost = feature_cost_coins(feature_key)
        if self.balance >= cost:
            self.balance -= cost
            return True
        return False
    
    def can_afford(self, feature_key: str) -> bool:
        """Проверить, хватает ли монет для функции"""
        cost = feature_cost_coins(feature_key)
        return self.balance >= cost
    
    def get_cost(self, feature_key: str) -> int:
        """Получить стоимость функции в монетах"""
        return feature_cost_coins(feature_key)

# Глобальные функции для совместимости со старым кодом
def get_balance(user_id: int) -> int:
    """Получить баланс пользователя"""
    # Здесь должна быть интеграция с базой данных
    # Пока возвращаем заглушку
    return 100  # Заглушка для тестирования

def charge_feature(user_id: int, feature_key: str) -> bool:
    """Списать монеты за функцию"""
    cost = feature_cost_coins(feature_key)
    # Здесь должна быть интеграция с базой данных
    return True  # Заглушка для тестирования

def buy_tariff(user_id: int, tariff_name: str) -> Dict[str, Any]:
    """Покупка тарифа"""
    tariffs = get_available_tariffs()
    for tariff in tariffs:
        if tariff["name"] == tariff_name:
            return {
                "success": True,
                "tariff": tariff,
                "payment_url": f"https://example.com/pay/{tariff_name}"  # Заглушка
            }
    return {"success": False, "error": "Tariff not found"}

def buy_topup(user_id: int, coins: int) -> Dict[str, Any]:
    """Покупка пакета пополнения"""
    packs = get_available_topup_packs()
    for pack in packs:
        if pack["coins"] == coins:
            return {
                "success": True,
                "pack": pack,
                "payment_url": f"https://example.com/pay/{coins}"  # Заглушка
            }
    return {"success": False, "error": "Pack not found"}

def get_user_tariff_info(user_id: int) -> Dict[str, Any]:
    """Получить информацию о тарифе пользователя"""
    # Здесь должна быть интеграция с базой данных
    return {
        "current_tariff": None,
        "expires_at": None,
        "is_active": False
    }

def get_transaction_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю транзакций пользователя"""
    # Здесь должна быть интеграция с базой данных
    return []  # Заглушка
