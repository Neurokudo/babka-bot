from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class Tariff:
    price_rub: int
    coins: int

TARIFFS: Dict[str, Tariff] = {
    "lite": Tariff(price_rub=1990, coins=120),
    "standard": Tariff(price_rub=2490, coins=210),
    "pro": Tariff(price_rub=4990, coins=440),
}

FEATURE_COSTS = {
    "video_8s_audio": 20,
    "video_8s_mute": 16,
    "image_basic": 1,
    "virtual_tryon": 3,
}

TOPUP_PACKS_RUB = {
    50:  990,
    120: 1990,
    250: 3990,
    500: 7490,
}

# для аналитики (не показывать пользователю)
COGS_USD = {
    "video_8s_audio": 1.20,
    "video_8s_mute": 0.80,
    "image_basic": 0.04,
    "virtual_tryon": 0.12,
}
