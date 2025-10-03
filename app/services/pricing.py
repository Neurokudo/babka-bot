from decimal import Decimal
from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS_RUB, COGS_USD

def coins_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].coins

def price_rub_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].price_rub

def feature_cost_coins(feature_key: str) -> int:
    return FEATURE_COSTS[feature_key]

def topup_price_rub(coins: int) -> int:
    return TOPUP_PACKS_RUB[coins]

def cogs_usd(feature_key: str) -> Decimal:
    return Decimal(str(COGS_USD[feature_key]))
