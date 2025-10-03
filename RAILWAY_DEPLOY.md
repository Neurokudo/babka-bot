# 🚀 Деплой на Railway

## Подготовка к деплою

1. **Убедитесь, что все изменения закоммичены:**
   ```bash
   git add .
   git commit -m "Готов к деплою"
   git push
   ```

2. **Проверьте конфигурацию:**
   - `railway.json` - настроен на запуск `webhook_server.py`
   - `Procfile` - содержит команды для release и worker
   - `requirements.txt` - содержит все зависимости

## Деплой на Railway

### Вариант 1: Через Railway CLI

1. **Установите Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Войдите в аккаунт:**
   ```bash
   railway login
   ```

3. **Создайте новый проект:**
   ```bash
   railway new
   ```

4. **Деплойте проект:**
   ```bash
   railway up
   ```

### Вариант 2: Через Railway Dashboard

1. **Перейдите на [railway.app](https://railway.app)**
2. **Нажмите "New Project"**
3. **Выберите "Deploy from GitHub repo"**
4. **Подключите репозиторий `babka-bot`**
5. **Railway автоматически определит конфигурацию из `railway.json`**

## Настройка переменных окружения

В Railway Dashboard перейдите в Settings → Variables и добавьте:

### Обязательные переменные:
- `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
- `ALLOWED_USERS` - список разрешенных пользователей (через запятую)
- `DATABASE_URL` - URL базы данных PostgreSQL

### Опциональные переменные:
- `YOOKASSA_SHOP_ID` - ID магазина в YooKassa
- `YOOKASSA_SECRET_KEY` - секретный ключ YooKassa
- `OPENAI_API_KEY` - ключ OpenAI для GPT функций
- `GCP_KEY_JSON_B64` - сервисный ключ Google Cloud (base64)
- `NANO_API_KEY` - ключ API для Nano
- `BG_REMOVAL_API_KEY` - ключ API для удаления фона

## Проверка деплоя

1. **Проверьте логи:**
   ```bash
   railway logs
   ```

2. **Проверьте статус:**
   ```bash
   railway status
   ```

3. **Проверьте webhook endpoint:**
   - URL будет показан в Railway Dashboard
   - Проверьте `/health` endpoint
   - Проверьте `/webhook/yookassa` endpoint

## Настройка Telegram Webhook

После успешного деплоя настройте webhook в Telegram:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-railway-app.railway.app/webhook/telegram"}'
```

## Мониторинг

- **Логи:** Railway Dashboard → Deployments → Logs
- **Метрики:** Railway Dashboard → Metrics
- **Переменные:** Railway Dashboard → Settings → Variables

## Troubleshooting

### Проблема: Приложение не запускается
- Проверьте логи на ошибки
- Убедитесь, что все переменные окружения настроены
- Проверьте, что `requirements.txt` содержит все зависимости

### Проблема: Webhook не работает
- Проверьте URL webhook в Telegram
- Убедитесь, что бот имеет права на webhook
- Проверьте логи на ошибки обработки webhook'ов

### Проблема: База данных не подключается
- Проверьте `DATABASE_URL`
- Убедитесь, что база данных доступна
- Проверьте миграции: `python RUN_MIGRATIONS.py`

