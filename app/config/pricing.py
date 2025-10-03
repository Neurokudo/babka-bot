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

TARIFFS: Dict[str, Tariff] = {
    "lite": Tariff(price_rub=1990, coins=120, duration_days=30),
    "standard": Tariff(price_rub=2490, coins=210, duration_days=30),
    "pro": Tariff(price_rub=4990, coins=440, duration_days=30),
}

FEATURE_COSTS = {
    "video_8s_audio": 20,
    "video_8s_mute": 16,
    "image_basic": 1,
    "virtual_tryon": 3,
    "transform": 1,  # Для трансформаций изображений
    "video": 20,    # Общий для видео
    "tryon": 3,     # Для виртуальной примерочной
    "json": 20,     # Для JSON генерации
}

TOPUP_PACKS: List[TopupPack] = [
    TopupPack(coins=50, price_rub=990),
    TopupPack(coins=120, price_rub=1990),
    TopupPack(coins=250, price_rub=3990),
    TopupPack(coins=500, price_rub=7490),
]

COGS_USD = {
    "video_8s_audio": 1.20,
    "video_8s_mute": 0.80,
    "image_basic": 0.04,
    "virtual_tryon": 0.12,
}
