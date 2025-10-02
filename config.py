# -*- coding: utf-8 -*-
"""
Конфигурация монет и тарифов
"""

# Стоимость операций в монетках
COST_VIDEO = 10           # монет за ролик 8с
COST_TRANSFORM = 1        # монет за любое фото-преобразование (базовое качество)
COST_TRANSFORM_PREMIUM = 1  # монет за преобразование (премиум качество) - тоже 1 монета
COST_TRYON = 1            # монет за виртуальную примерочную - тоже 1 монета
FREE_RETRY_PER_JOB = 1    # 1 бесплатный повтор

# Дневные лимиты по видео
DAILY_CAP_VIDEOS = {
    "light": 3, 
    "standard": 5, 
    "pro": 10
}

# Тарифы (подписки с монетками)
PLANS = {
    "lite": {
        "name": "Лайт", 
        "price_rub": 1990, 
        "coins": 120,  # 10 видео (100) + 20 фото (20) = 120 монет
        "description": "🎬 10 видео + 📸 20 фото"
    },
    "std": {
        "name": "Стандарт", 
        "price_rub": 2490, 
        "coins": 210,  # 16 видео (160) + 50 фото (50) = 210 монет
        "description": "🎬 16 видео + 📸 50 фото",
        "recommended": True
    },
    "pro": {
        "name": "Про", 
        "price_rub": 4990, 
        "coins": 440,  # 32 видео (320) + 120 фото (120) = 440 монет
        "description": "🎬 32 видео + 📸 120 фото"
    },
}

# Докупки (аддоны)
ADDONS = {
    "v5": {"title": "Video 5 — 1 190 ₽", "price_rub": 1190, "coins": 50, "videos": 5, "photos": 0},
    "v10": {"title": "Video 10 — 2 190 ₽", "price_rub": 2190, "coins": 100, "videos": 10, "photos": 0},
    "p20": {"title": "Photo 20 — 590 ₽", "price_rub": 590, "coins": 20, "videos": 0, "photos": 20},
    "p50": {"title": "Photo 50 — 1 190 ₽", "price_rub": 1190, "coins": 50, "videos": 0, "photos": 50},
    "mix": {"title": "Mix — 1 690 ₽", "price_rub": 1690, "coins": 70, "videos": 5, "photos": 20},
}

# Разовые пакеты монеток (дороже подписок)
TOP_UPS = [
    {"coins": 20, "price_rub": 390, "label": "~19,5 ₽/монета"},
    {"coins": 50, "price_rub": 890, "label": "~17,8 ₽/монета"},
    {"coins": 100, "price_rub": 1490, "label": "~14,9 ₽/монета"},
    {"coins": 300, "price_rub": 3990, "label": "~13,3 ₽/монета"},
    {"coins": 700, "price_rub": 9990, "label": "~14,2 ₽/монета"},
]

# Качество/размер изображений
IMG_SIZE = {
    "basic": 1024, 
    "premium": 2048
}

QUALITY = {
    "basic": "fast", 
    "premium": "high"
}

# Безопасные дефолты
DEFAULT_OUTPUT_FMT = "png"
DEFAULT_SEED = None

# Уведомления
LOW_COINS_THRESHOLD = 15  # уведомление при остатке < 15 монет
