# Настройка Telegram Webhook для Babka Bot

## Реализованные функции

✅ **Переключаемый режим работы**: `TELEGRAM_MODE=polling|webhook` (по умолчанию `polling`)
✅ **Логирование**: Все входящие апдейты и callback'и логируются
✅ **Единый источник тарифов**: Все экраны используют `app/services/pricing.py`
✅ **Health check**: `GET /health` возвращает `{"ok": true}`
✅ **Webhook endpoint**: `POST /webhook/{BOT_TOKEN}` для Telegram
✅ **YooKassa webhook**: `POST /webhook/yookassa` для платежей

## Переменные окружения

```bash
# Обязательные
BOT_TOKEN=your_telegram_bot_token
TELEGRAM_MODE=polling  # или webhook
PORT=8080  # Railway автоматически устанавливает

# YooKassa (обязательные для платежей)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Опциональные
PUBLIC_URL=https://your-domain.railway.app  # для setWebhook
```

## Этап 1: Тестирование Polling режима

1. **Установите переменные окружения в Railway:**
   ```
   TELEGRAM_MODE=polling
   BOT_TOKEN=your_bot_token
   YOOKASSA_SHOP_ID=your_shop_id
   YOOKASSA_SECRET_KEY=your_secret_key
   ```

2. **Redeploy в Railway**

3. **Проверьте логи:**
   - Должно появиться: `Bot started in polling mode`
   - Должно появиться: `Bot token suffix: XXXXXX`

4. **Протестируйте бота:**
   - Нажмите любую кнопку в боте
   - В логах должно появиться: `CALLBACK show_tariffs uid=XXXXXX`
   - Экран "Тарифы" должен показать: 1990/2490/4990 ₽ → 120/210/440 монет

## Этап 2: Переход на Webhook режим

1. **Обновите переменные окружения:**
   ```
   TELEGRAM_MODE=webhook
   PUBLIC_URL=https://your-domain.railway.app
   ```

2. **Redeploy в Railway**

3. **Проверьте health check:**
   ```
   curl https://your-domain.railway.app/health
   # Должно вернуть: {"ok": true}
   ```

4. **Настройте webhook в Telegram:**

   **Сброс старого webhook:**
   ```
   https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook
   ```

   **Установка нового webhook:**
   ```
   https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://your-domain.railway.app/webhook/{BOT_TOKEN}&allowed_updates=["message","callback_query"]&drop_pending_updates=true
   ```

5. **Проверьте webhook:**
   ```
   https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo
   # Поле "url" должно быть заполнено
   ```

6. **Протестируйте бота:**
   - Нажмите кнопку в боте
   - В логах должно появиться: `WEBHOOK HIT: method=POST path=/webhook/XXXXXX`
   - Затем: `CALLBACK show_tariffs uid=XXXXXX`

## Структура тарифов

Все тарифы берутся из `app/config/pricing.py`:

```python
TARIFFS = {
    "lite": Tariff(price_rub=1990, coins=120, duration_days=30),
    "standard": Tariff(price_rub=2490, coins=210, duration_days=30), 
    "pro": Tariff(price_rub=4990, coins=440, duration_days=30),
}
```

## Логирование

Все ключевые события логируются:

- `Bot started in {mode} mode` - при старте
- `Bot token suffix: XXXXXX` - информация о токене
- `WEBHOOK HIT: method=POST path=/webhook/XXXXXX` - входящие webhook'и
- `CALLBACK {callback_data} uid={user_id}` - все callback'и
- `CALLBACK show_tariffs uid={user_id}` - показ тарифов

## Troubleshooting

**Проблема**: Бот не отвечает на кнопки
**Решение**: Проверьте, что `TELEGRAM_MODE=polling` и в логах есть `CALLBACK` сообщения

**Проблема**: Webhook не работает
**Решение**: 
1. Проверьте `GET /health` - должен возвращать `{"ok": true}`
2. Проверьте `getWebhookInfo` - поле `url` должно быть заполнено
3. Проверьте логи на `WEBHOOK HIT` сообщения

**Проблема**: Старые тексты тарифов
**Решение**: Все тексты уже используют единый источник из `app/services/pricing.py`

## Файлы

- `main.py` - основная логика бота с переключателем режимов
- `app/web/telegram_web.py` - обработка Telegram webhook'ов
- `webhook_server.py` - объединенный сервер для Telegram и YooKassa
- `app/services/pricing.py` - единый источник тарифов
- `app/config/pricing.py` - конфигурация тарифов
