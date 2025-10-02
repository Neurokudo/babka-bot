# Babka Bot · Cursor Onboarding

Используй этот промт как вводный контекст при начале работы над задачей.

## Что делает проект
- Telegram-бот, который генерирует видео (Veo 3), обрабатывает фото (Gemini 2.5), делает виртуальную примерку (Vertex AI VTO) и поддерживает JSON-режим для power users.
- Монетизация через YooKassa. Балансы, бонусы и подписки ведутся в PostgreSQL.
- Архитектура, клавиатуры и все пользовательские потоки задокументированы в `ARCHITECTURE.md`.

## Основные правила
1. Пользовательские операции всегда проходят через `billing.py` (hold_and_start → on_success/on_error).
2. Права доступа проверяются по списку `ALLOWED_USERS` до публичного релиза.
3. Любая генерация отправляет прогресс/результаты через Inline и Reply-клавиатуры.
4. После ошибок генерации ресурсы должны возвращаться автоматически.
5. Платежи обрабатываются webhook'ом (`webhook_server.py`) и дублируются в БД.

## Полезные команды
- `python main.py` — локальный бот (polling).
- `python webhook_server.py` — локальный webhook-сервер.
- `python test_complete_payment_system.py` — интеграционные тесты платежей (нужны тестовые ключи YooKassa).
- `pytest` — unit-тесты (по мере добавления).

## Слои системы
- `main.py` — entrypoint, команды и клавиатуры.
- `billing.py`, `subscription_system.py`, `database.py` — монеты, подписки, транзакции.
- `veo_client.py`, `transforms_client.py`, `tryon_client.py`, `nano_client.py` — обёртки над внешними AI-сервисами.
- `payment_yookassa.py` — интеграция YooKassa.
- `ARCHITECTURE.md` — exhaustive UX map.

Убедись, что перед пушем:
- Обновлены документация и `.env.example` для новых переменных.
- Добавлены тесты/моки для новых API вызовов.
- Прогоняются `pytest` и критические интеграционные тесты.
