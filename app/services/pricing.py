from decimal import Decimal
from typing import Dict, List, Tuple

from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS_RUB, COGS_USD, Tariff


def coins_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].coins


def price_rub_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].price_rub


def feature_cost_coins(key: str) -> int:
    return FEATURE_COSTS[key]


def topup_price_rub(coins: int) -> int:
    return TOPUP_PACKS_RUB[coins]


def cogs_usd(key: str) -> Decimal:
    return Decimal(str(COGS_USD[key]))


def all_tariffs() -> List[Tuple[str, str, int, int]]:
    mapping = {"lite": "✨ Лайт", "standard": "⭐ Стандарт", "pro": "💎 Про"}
    return [(code, mapping[code], t.price_rub, t.coins) for code, t in TARIFFS.items()]


def all_topups() -> List[Tuple[int, int]]:
    return sorted(TOPUP_PACKS_RUB.items(), key=lambda x: x[0])


# Convenience formatting helpers for UI
def get_available_tariffs() -> Dict[str, Dict[str, int]]:
    return {k: {"price": v.price_rub, "coins": v.coins, "name": ("✨ Лайт" if k == "lite" else "⭐ Стандарт" if k == "standard" else "💎 Про")} for k, v in TARIFFS.items()}


def get_available_topup_packs() -> Dict[int, int]:
    return dict(TOPUP_PACKS_RUB)


def pricing_text() -> str:
    parts: List[str] = []
    parts.append("💰 <b>Тарифы (30 дней)</b>\n")
    for code, name, price_rub, coins in all_tariffs():
        parts.append(f"{name} — {price_rub:,} ₽\n🎟 {coins} монет\n")
    parts.append("\n🎬 <b>Видео (8 сек)</b>\n🔊 Со звуком — 20 монет\n🔇 Без звука — 16 монет\n")
    parts.append("\n📸 Фото-инструменты — 1 монета\n👗 Примерка одежды — 3 монеты\n")
    topups = all_topups()
    topup_pairs = []
    for i in range(0, len(topups), 2):
        pair = topups[i:i+2]
        line = " · ".join([f"{c} — {p:,} ₽" for c, p in pair])
        topup_pairs.append(line)
    parts.append("\n➕ <b>Пополнить монеты</b>\n" + "\n".join(topup_pairs))
    parts.append("\n\n<i>*Докупка монет не продлевает подписку.</i>")
    return "\n".join(parts)


def format_plans_list() -> str:
    lines: List[str] = []
    lines.append("💰 <b>Тарифы (30 дней)</b>\n")
    for code, name, price_rub, coins in all_tariffs():
        lines.append(f"{name} — {price_rub:,} ₽\n🎟 {coins} монет\n")
    return "\n".join(lines).strip()


def format_feature_costs() -> str:
    return (
        "\n🎬 <b>Видео (8 сек)</b>\n"
        "🔊 Со звуком — 20 монет\n"
        "🔇 Без звука — 16 монет\n\n"
        "📸 Фото-инструменты — 1 монета\n"
        "👗 Примерка одежды — 3 монеты"
    )


def calculate_coin_rate_rub(tariff_name: str) -> Decimal:
    t: Tariff = TARIFFS[tariff_name]
    return Decimal(t.price_rub) / Decimal(t.coins)


def calculate_coin_rate_rub_topup(coins: int) -> Decimal:
    price = TOPUP_PACKS_RUB[coins]
    return Decimal(price) / Decimal(coins)


