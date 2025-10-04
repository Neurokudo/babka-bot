from decimal import Decimal
from typing import List, Dict, Any
from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS, COGS_USD

def coins_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].coins

def price_rub_for_tariff(tariff_name: str) -> int:
    return TARIFFS[tariff_name].price_rub

def feature_cost_coins(feature_key: str) -> int:
    return FEATURE_COSTS.get(feature_key, 1)

def topup_price_rub(coins: int) -> int:
    for pack in TOPUP_PACKS:
        if pack.coins == coins:
            return pack.price_rub
    return 0

def cogs_usd(feature_key: str) -> Decimal:
    return Decimal(str(COGS_USD.get(feature_key, 0.01)))

def get_available_tariffs() -> List[Dict[str, Any]]:
    """Получить список доступных тарифов"""
    return [
        {
            "name": "lite",
            "title": "Лайт",
            "price_rub": TARIFFS["lite"].price_rub,
            "coins": TARIFFS["lite"].coins,
            "duration_days": TARIFFS["lite"].duration_days,
            "icon": "✨"
        },
        {
            "name": "standard", 
            "title": "Стандарт",
            "price_rub": TARIFFS["standard"].price_rub,
            "coins": TARIFFS["standard"].coins,
            "duration_days": TARIFFS["standard"].duration_days,
            "icon": "⭐"
        },
        {
            "name": "pro",
            "title": "Про", 
            "price_rub": TARIFFS["pro"].price_rub,
            "coins": TARIFFS["pro"].coins,
            "duration_days": TARIFFS["pro"].duration_days,
            "icon": "💎"
        }
    ]

def get_tariff_by_name(tariff_name: str) -> Dict[str, Any]:
    """Получить тариф по имени"""
    tariffs_list = get_available_tariffs()
    for tariff in tariffs_list:
        if tariff["name"] == tariff_name:
            return tariff
    return None

def get_available_topup_packs() -> List[Dict[str, Any]]:
    """Получить список доступных пакетов пополнения"""
    return [
        {
            "coins": pack.coins,
            "price_rub": pack.price_rub,
            "rate_rub_per_coin": round(pack.price_rub / pack.coins, 2)
        }
        for pack in TOPUP_PACKS
    ]

def calculate_coin_rate_rub(tariff_name: str) -> float:
    """Рассчитать стоимость монеты в рублях для тарифа"""
    tariff = TARIFFS[tariff_name]
    return round(tariff.price_rub / tariff.coins, 2)

def calculate_coin_rate_rub_topup(coins: int) -> float:
    """Рассчитать стоимость монеты в рублях для пакета пополнения"""
    for pack in TOPUP_PACKS:
        if pack.coins == coins:
            return round(pack.price_rub / pack.coins, 2)
    return 0

def format_plans_list() -> str:
    """Форматированный список тарифов для UI"""
    plans = []
    for tariff_data in get_available_tariffs():
        plans.append(
            f"{tariff_data['icon']} {tariff_data['title']} — {tariff_data['price_rub']} ₽\n"
            f"🎟 {tariff_data['coins']} монет"
        )
    return "\n\n".join(plans)

def format_feature_costs() -> str:
    """Форматированный список стоимости функций"""
    costs = []
    
    # Видео
    costs.append("🎬 Видео (8 сек)")
    costs.append(f"🔊 Со звуком — {FEATURE_COSTS['video_8s_audio']} монет")
    costs.append(f"🔇 Без звука — {FEATURE_COSTS['video_8s_mute']} монет")
    
    # Фото и примерка
    costs.append("")
    costs.append(f"📸 Фото-инструменты — {FEATURE_COSTS['image_basic']} монета")
    costs.append(f"👗 Примерка одежды — {FEATURE_COSTS['virtual_tryon']} монеты")
    
    return "\n".join(costs)

def format_topup_packs() -> str:
    """Форматированный список пакетов пополнения"""
    packs = ["➕ Пополнить монеты"]
    for pack in TOPUP_PACKS:
        rate = round(pack.price_rub / pack.coins, 2)
        packs.append(f"{pack.coins} — {pack.price_rub} ₽")
    packs.append("")
    packs.append("Примечание: «Докупка монет не продлевает подписку».")
    return "\n".join(packs)

def pricing_text() -> str:
    """Полный текст с тарифами и стоимостью"""
    text = "💰 Тарифы (30 дней)\n\n"
    text += format_plans_list()
    text += "\n\n"
    text += format_feature_costs()
    text += "\n\n"
    text += format_topup_packs()
    return text
