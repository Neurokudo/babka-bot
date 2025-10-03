from decimal import Decimal
from typing import Dict
from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS_RUB, COGS_USD, Tariff

def coins_for_tariff(tariff_name: str) -> int:
    """Получить количество монет для тарифа"""
    return TARIFFS[tariff_name].coins

def price_rub_for_tariff(tariff_name: str) -> int:
    """Получить цену в рублях для тарифа"""
    return TARIFFS[tariff_name].price_rub

def feature_cost_coins(feature_key: str) -> int:
    """Получить стоимость функции в монетах"""
    return FEATURE_COSTS[feature_key]

def topup_price_rub(coins: int) -> int:
    """Получить цену в рублях для пакета пополнения"""
    return TOPUP_PACKS_RUB[coins]

def cogs_usd(feature_key: str) -> Decimal:
    """Получить себестоимость функции в долларах"""
    return Decimal(str(COGS_USD[feature_key]))

def get_available_tariffs() -> Dict[str, Tariff]:
    """Получить все доступные тарифы"""
    return TARIFFS

def get_available_topup_packs() -> Dict[int, int]:
    """Получить все доступные пакеты пополнения"""
    return TOPUP_PACKS_RUB

def get_available_features() -> Dict[str, int]:
    """Получить все доступные функции и их стоимость"""
    return FEATURE_COSTS

def calculate_coin_rate_rub(tariff_name: str) -> float:
    """Рассчитать стоимость 1 монеты в рублях для тарифа"""
    tariff = TARIFFS[tariff_name]
    return tariff.price_rub / tariff.coins

def calculate_coin_rate_rub_topup(coins: int) -> float:
    """Рассчитать стоимость 1 монеты в рублях для пакета пополнения"""
    return TOPUP_PACKS_RUB[coins] / coins
