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

def format_plans_list() -> str:
    """Форматирование списка тарифов для пользователей"""
    lines = ["💰 <b>Тарифы (30 дней)</b>\n"]
    tariffs = get_available_tariffs()
    for key, tariff in tariffs.items():
        rate = calculate_coin_rate_rub(key)
        line_parts = [
            f"🎟 {tariff.coins} монет",
            f"{tariff.price_rub:,} ₽",
            f"~{rate:.1f} ₽/монета"
        ]
        lines.append(" · ".join(line_parts))
    
    lines.append("\n💡 Докупка монет не продлевает подписку.")
    return "\n".join(lines)

def format_feature_costs() -> str:
    """Форматирование стоимости функций для пользователей"""
    lines = ["🎬 <b>Видео (8 сек)</b>"]
    lines.append("🔊 Со звуком — 20 монет")
    lines.append("🔇 Без звука — 16 монет")
    lines.append("")
    lines.append("📸 <b>Фото-инструменты</b> — 1 монета")
    lines.append("👗 <b>Примерка одежды</b> — 3 монеты")
    return "\n".join(lines)

def pricing_text() -> str:
    """Полный текст с тарифами и стоимостью функций"""
    plans_text = format_plans_list()
    costs_text = format_feature_costs()
    return f"{plans_text}\n\n{costs_text}"
