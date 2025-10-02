# -*- coding: utf-8 -*-
"""
Конфигурация монет и тарифов
"""

# Стоимость операций
COST_VIDEO = 10           # монет за ролик 8с
COST_TRANSFORM = 1        # монет за любое фото-преобразование (1024x1024)
COST_TRANSFORM_PREMIUM = 2  # монет за преобразование (2048x2048 или сложные)
COST_TRYON = 5            # монет за виртуальную примерочную
FREE_RETRY_PER_JOB = 1    # 1 бесплатный повтор

# Дневные лимиты по видео
DAILY_CAP_VIDEOS = {
    "light": 3, 
    "standard": 5, 
    "pro": 10
}

# Тарифы (новые согласно brief)
PLANS = {
    "lite": {
        "name": "Лайт", 
        "price_rub": 1990, 
        "coins": 120,
        "videos": 10, 
        "photos": 20
    },
    "std": {
        "name": "Стандарт", 
        "price_rub": 2490, 
        "coins": 200,
        "videos": 16, 
        "photos": 50, 
        "recommended": True
    },
    "pro": {
        "name": "Про", 
        "price_rub": 4990, 
        "coins": 400,
        "videos": 32, 
        "photos": 120
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

# Докупки монет (старые, для совместимости)
TOP_UPS = [
    {"coins": 20, "price_rub": 590, "label": "Хит"},
    {"coins": 50, "price_rub": 1190, "label": "Экономия 10%"},
    {"coins": 100, "price_rub": 2190, "label": "Экономия 15%"},
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

# Админские права
ADMIN_USER_ID = 5015100177  # ID администратора с неограниченным доступом
