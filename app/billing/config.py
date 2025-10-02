# -*- coding: utf-8 -*-
"""
app/billing/config.py - Единый источник правды для всех цен и планов
"""

# Стоимость операций в монетах
COST_VIDEO = 10           # монет за ролик 8с
COST_TRANSFORM = 1        # монет за любое фото-преобразование (базовое качество)
COST_TRANSFORM_PREMIUM = 2  # монет за преобразование (премиум качество)
COST_TRYON = 1            # монет за виртуальную примерочную

# Тарифы (подписки с монетками)
PLANS = {
    "lite": {
        "name": "Лайт", 
        "price_rub": 1990, 
        "coins": 120,  # ~16.6 ₽/монета
    },
    "std": {
        "name": "Стандарт", 
        "price_rub": 2490, 
        "coins": 210,  # ~11.9 ₽/монета ⭐ выгоднее
        "recommended": True
    },
    "pro": {
        "name": "Про", 
        "price_rub": 4990, 
        "coins": 440,  # ~11.3 ₽/монета ⭐ самый выгодный
    },
}

# Разовые пополнения (дороже подписок за 1 монету)
TOP_UPS = [
    {"coins": 20, "price_rub": 390, "label": "~19,5 ₽/монета"},
    {"coins": 50, "price_rub": 890, "label": "~17,8 ₽/монета"},
    {"coins": 100, "price_rub": 1490, "label": "~14,9 ₽/монета"},
    {"coins": 300, "price_rub": 3990, "label": "~13,3 ₽/монета"},
    {"coins": 700, "price_rub": 9990, "label": "~14,2 ₽/монета"},
]

# Дополнительные пакеты (дороже обычных пакетов)
ADDONS = {
    "v5": {"title": "Video 5 — 1 190 ₽", "price_rub": 1190, "coins": 50, "description": "5 видео"},
    "v10": {"title": "Video 10 — 2 190 ₽", "price_rub": 2190, "coins": 100, "description": "10 видео"},
    "p20": {"title": "Photo 20 — 590 ₽", "price_rub": 590, "coins": 20, "description": "20 фото"},
    "p50": {"title": "Photo 50 — 1 190 ₽", "price_rub": 1190, "coins": 50, "description": "50 фото"},
    "mix": {"title": "Mix — 1 690 ₽", "price_rub": 1690, "coins": 70, "description": "5 видео + 20 фото"},
}

# Качество/размер изображений
IMG_SIZE = {
    "basic": 1024, 
    "premium": 2048
}

QUALITY = {
    "basic": "fast", 
    "premium": "high"
}

# Уведомления
LOW_COINS_THRESHOLD = 15  # уведомление при остатке < 15 монет

# Безопасные дефолты
DEFAULT_OUTPUT_FMT = "png"
DEFAULT_SEED = None

# Админ ID
ADMIN_ID = 5015100177

# Бонусы приветствия (один раз)
WELCOME_BONUSES = {
    "video_bonus": 2,  # 2 видео = 20 монет
    "photo_bonus": 3,  # 3 фото = 3 монеты
    "tryon_bonus": 1,  # 1 примерочная = 1 монета
    "total_coins": 24  # общий эквивалент в монетах
}
