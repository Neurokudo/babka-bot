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
