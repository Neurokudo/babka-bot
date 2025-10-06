from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass(frozen=True)
class Tariff:
    price_rub: int
    coins: int
    duration_days: int = 30

@dataclass(frozen=True)
class TopupPack:
    coins: int
    price_rub: int

@dataclass(frozen=True)
class SpecialPack:
    name: str
    description: str
    price_rub: int
    items: Dict[str, int]  # {"video_8s_mute": 1, "virtual_tryon": 10}
    duration_days: int = 7
    one_time_only: bool = True

TARIFFS: Dict[str, Tariff] = {
    "lite": Tariff(price_rub=1990, coins=240, duration_days=30),
    "standard": Tariff(price_rub=2490, coins=330, duration_days=30),
    "pro": Tariff(price_rub=4990, coins=700, duration_days=30),
}

# Расширенная система ценообразования с метками фич для аудита
FEATURE_COSTS = {
    "video_6s_mute": 14,     # 6 сек, без звука
    "video_8s_mute": 18,     # 8 сек, без звука
    "video_8s_audio": 26,    # 8 сек, со звуком
    "image_basic": 1,        # Фото-инструменты
    "virtual_tryon": 3,      # Виртуальная примерочная
    "transform": 1,          # Для трансформаций изображений
    "video": 26,            # Общий для видео (по умолчанию 8с со звуком)
    "tryon": 3,             # Для виртуальной примерочной
    "json": 26,             # Для JSON генерации
}

# Детальные описания фич для аудита и отчетов
FEATURE_DESCRIPTIONS = {
    "video_6s_mute": "Veo 3 - 6 сек без звука",
    "video_8s_mute": "Veo 3 - 8 сек без звука", 
    "video_8s_audio": "Veo 3 - 8 сек со звуком",
    "image_basic": "Фото-инструменты (базовые)",
    "virtual_tryon": "Виртуальная примерочная (Try-On)",
    "transform": "Трансформации изображений",
    "video": "Видео генерация (общая)",
    "tryon": "Виртуальная примерочная",
    "json": "JSON генерация",
    "subscription_lite": "Подписка Лайт",
    "subscription_standard": "Подписка Стандарт", 
    "subscription_pro": "Подписка Про",
    "topup": "Пополнение монет",
    "bonus_gift": "Бонусный подарок",
    "admin_set_balance": "Админская установка баланса",
    "manual_add": "Ручное добавление монет",
    "manual_spend": "Ручное списание монет"
}

# Категории фич для группировки в отчетах
FEATURE_CATEGORIES = {
    "video_generation": ["video_6s_mute", "video_8s_mute", "video_8s_audio", "video"],
    "photo_tools": ["image_basic", "transform"],
    "virtual_tryon": ["virtual_tryon", "tryon"],
    "subscriptions": ["subscription_lite", "subscription_standard", "subscription_pro"],
    "topup": ["topup"],
    "bonuses": ["bonus_gift"],
    "admin": ["admin_set_balance", "manual_add", "manual_spend"],
    "other": ["json"]
}

TOPUP_PACKS: List[TopupPack] = [
    TopupPack(coins=50, price_rub=990),
    TopupPack(coins=120, price_rub=1990),
    TopupPack(coins=250, price_rub=3990),
    TopupPack(coins=500, price_rub=7490),
]

SPECIAL_PACKS: List[SpecialPack] = [
    SpecialPack(
        name="starter_pack",
        description="10 фото (переодевание) + 1 видео",
        price_rub=349,
        items={"video_8s_mute": 1, "virtual_tryon": 10},
        duration_days=7,
        one_time_only=True
    )
]

COGS_USD = {
    "video_6s_mute": 0.70,
    "video_8s_mute": 0.80,
    "video_8s_audio": 1.20,
    "image_basic": 0.04,
    "virtual_tryon": 0.12,
}
