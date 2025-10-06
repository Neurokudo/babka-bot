from decimal import Decimal
from typing import List, Dict, Any
from app.config.pricing import TARIFFS, FEATURE_COSTS, TOPUP_PACKS, SPECIAL_PACKS, COGS_USD

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
    try:
        plans = []
        
        # Заголовок
        plans.append("💰 <b>Тарифы на 30 дней</b>\n")
        
        for tariff_data in get_available_tariffs():
            plans.append(f"{tariff_data['icon']} {tariff_data['title']} — {tariff_data['price_rub']:,} ₽ → {tariff_data['coins']} монет")
            plans.append(f"Что это даёт:")
            examples = calculate_tariff_examples(tariff_data['coins'])
            plans.append(examples)
            plans.append("")  # Пустая строка между тарифами
        
        # Добавляем информацию о стоимости функций
        plans.append(format_feature_costs())
        plans.append("")
        plans.append("💡 Подсказка пользователю: без звука — дешевле, роликов выйдет больше. Звук можно включить по желанию.\n")
        
        # Добавляем разовый пакет
        plans.append(format_special_packs())
        
        return "\n".join(plans)
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.error("Failed to build plans list: %s", e, exc_info=True)
        return "❌ Ошибка при загрузке тарифов. Попробуйте ещё раз."

def calculate_tariff_examples(coins: int) -> str:
    """Рассчитать примеры использования для тарифа"""
    examples = []
    
    # Видео 6 сек без звука
    video_6s_count = coins // FEATURE_COSTS["video_6s_mute"]
    if video_6s_count > 0:
        examples.append(f"* до {video_6s_count} видео (6 сек, без звука) или")
    
    # Видео 8 сек без звука
    video_8s_mute_count = coins // FEATURE_COSTS["video_8s_mute"]
    if video_8s_mute_count > 0:
        examples.append(f"* до {video_8s_mute_count} видео (8 сек, без звука) или")
    
    # Видео 8 сек со звуком
    video_8s_audio_count = coins // FEATURE_COSTS["video_8s_audio"]
    if video_8s_audio_count > 0:
        examples.append(f"* до {video_8s_audio_count} видео (8 сек, со звуком) или")
    
    # Фото-операции
    photo_count = coins // FEATURE_COSTS["image_basic"]
    if photo_count > 0:
        examples.append(f"* до {photo_count} фото-операций")
    
    return "\n".join(examples)

def format_feature_costs() -> str:
    """Форматированный список стоимости функций"""
    costs = []
    
    # Заголовок
    costs.append("💡 <b>Как списываются монетки:</b>")
    
    # Видео
    costs.append("🎬 Видео Veo 3:")
    costs.append("• 6 сек, без звука — 14 монеток")
    costs.append("• 8 сек, без звука — 18 монеток")
    costs.append("• 8 сек, со звуком — 26 монеток")
    
    # Фото и примерка
    costs.append("📸 Фото-инструменты — 1 монетка за действие")
    costs.append("👗 Виртуальная примерочная (Try-On) — 3 монетки за 1 образ (1 результат)")
    
    return "\n".join(costs)

def format_topup_packs() -> str:
    """Форматированный список пакетов пополнения"""
    packs = []
    for pack in TOPUP_PACKS:
        packs.append(f"{pack.coins} монеток — {pack.price_rub} ₽")
    return "\n".join(packs)

def get_available_special_packs() -> List[Dict[str, Any]]:
    """Получить список доступных разовых пакетов"""
    return [
        {
            "name": pack.name,
            "description": pack.description,
            "price_rub": pack.price_rub,
            "items": pack.items,
            "duration_days": pack.duration_days,
            "one_time_only": pack.one_time_only
        }
        for pack in SPECIAL_PACKS
    ]

def format_special_packs() -> str:
    """Форматированный список разовых пакетов"""
    packs = []
    packs.append("🎁 <b>Разовый выгодный пакет</b>")
    
    for pack in SPECIAL_PACKS:
        packs.append(f"{pack.description} — {pack.price_rub} ₽")
        
        # Детализация содержимого
        items_desc = []
        for item, count in pack.items.items():
            if item == "video_8s_mute":
                items_desc.append(f"* {count} видео Veo 3 (8 сек, без звука) в подарок")
            elif item == "virtual_tryon":
                items_desc.append(f"* {count} запусков Переодеваний (по 1 результату)")
        
        if items_desc:
            packs.append("\n".join(items_desc))
        
        packs.append(f"* Активация: {pack.duration_days} дней")
        if pack.one_time_only:
            packs.append("* Покупка: 1 раз на пользователя")
    
    return "\n".join(packs)

def pricing_text() -> str:
    """Полный текст с тарифами и стоимостью"""
    text = "💰 Тарифы на 30 дней\n\n"
    
    # Добавляем детальные описания тарифов
    for tariff_data in get_available_tariffs():
        text += f"{tariff_data['icon']} {tariff_data['title']} — {tariff_data['price_rub']} ₽ → {tariff_data['coins']} монеток\n"
        text += f"Что это даёт:\n"
        text += calculate_tariff_examples(tariff_data['coins'])
        text += "\n\n"
    
    text += format_feature_costs()
    text += "\n\n"
    text += "💡 Подсказка пользователю: без звука — дешевле, роликов выйдет больше. Звук можно включить по желанию.\n\n"
    text += format_special_packs()
    text += "\n\n"
    text += "➕ Пакеты монеток:\n"
    text += format_topup_packs()
    text += "\n\n💡 Докупка монеток не продлевает подписку."
    return text
