# Babka Bot

Telegram бот для генерации AI контента с использованием Veo, Gemini и других AI сервисов.

## Структура проекта

```
babka-bot-clean/
├── main.py                    # Главный файл бота
├── requirements.txt           # Зависимости Python
├── Procfile                  # Конфигурация для Railway
├── runtime.txt               # Версия Python
├── .railwayignore           # Исключения для Railway
└── app/                     # Основная директория приложения
    ├── config/
    │   └── pricing.py        # Конфигурация тарифов
    ├── services/
    │   ├── pricing.py        # Сервис тарифов
    │   ├── wallet.py         # Сервис кошелька
    │   ├── billing.py        # Сервис биллинга
    │   └── clients/          # AI клиенты
    │       ├── veo_client.py
    │       ├── nano_client.py
    │       ├── tryon_client.py
    │       └── transforms_client.py
    ├── db/
    │   └── queries.py        # База данных
    └── utils/
        └── logging.py        # Логирование
```

## Локальный запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` с переменными окружения:
```
TELEGRAM_TOKEN=your_bot_token
GCP_PROJECT_ID=your_gcp_project
GCP_KEY_JSON_B64=your_gcp_credentials
```

3. Запустите бота:
```bash
python main.py
```

## Деплой на Railway

Проект готов для деплоя на Railway. Все необходимые файлы настроены:
- `Procfile` - команда запуска
- `requirements.txt` - зависимости
- `runtime.txt` - версия Python
- `.railwayignore` - исключения

## Тарифы

- ✨ Лайт — 1 990 ₽ → 120 монет
- ⭐ Стандарт — 2 490 ₽ → 210 монет  
- 💎 Про — 4 990 ₽ → 440 монет

## Функции

- 🎬 Генерация видео (Veo)
- 🖼️ Обработка изображений (Gemini)
- 👗 Виртуальная примерочная
- 📸 Трансформации фото
