from typing import Optional
from decimal import Decimal
from app.services.pricing import feature_cost_coins

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
