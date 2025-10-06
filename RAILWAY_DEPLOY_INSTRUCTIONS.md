# 🚀 Инструкции по деплою и исправлению в Railway

## ✅ Что исправлено

1. **Legacy shim исправлен** - теперь использует `@router.callback_query` вместо `@dp.callback_query`
2. **Добавлено логирование** - `⚡ LEGACY SHIM ACTIVATED` для отладки
3. **Созданы скрипты** для исправления баланса в PostgreSQL Railway

## 🔧 Следующие шаги

### 1. Исправить баланс в Railway PostgreSQL

Зайдите в **Railway → ваш сервис → Shell** и выполните:

```bash
python scripts/set_balance_postgres.py
```

**Ожидаемый результат:**
```
🔧 Connecting to PostgreSQL: postgresql://...
💰 Current balance: 1625
✅ Balance updated: old=1625, new=100
```

### 2. Проверить деплой

В том же Shell выполните:

```bash
python scripts/deploy_check.py
```

**Ожидаемый результат:**
```
✅ DATABASE_URL found: postgresql://...
✅ Connected to DB, user 5015100177 balance: 100
✅ Pricing service working, 3 tariffs available
✅ Plans text generated, length: 1143 chars
✅ All checks passed!
```

### 3. Проверить работу кнопки "Тарифы"

После исправления баланса:

1. **Профиль** → должно показать "💰 Монет: 100"
2. **Тарифы** → должен открыться без ошибок
3. **В логах Railway** должно появиться: `⚡ LEGACY SHIM ACTIVATED for show_tariffs`

## 🔍 Ожидаемые результаты

| Проверка | Ожидаемый результат |
|----------|-------------------|
| Профиль / Баланс | 💰 Монет: 100 |
| Тарифы | Работает, без ошибок |
| Логи Railway | ⚡ LEGACY SHIM ACTIVATED for show_tariffs |
| Пополнить монеты | Работает |
| Фото-инструменты | Баланс уменьшается на 1 |

## 🐛 Что было исправлено

- ❌ **Проблема**: Legacy shim не срабатывал (`@dp.callback_query` не существует)
- ✅ **Решение**: Заменен на `@router.callback_query`
- ❌ **Проблема**: Баланс 1625 вместо 100
- ✅ **Решение**: Скрипт `set_balance_postgres.py` для PostgreSQL Railway

## 📝 Технические детали

1. **Legacy shim** теперь правильно использует `router` вместо `dp`
2. **Скрипт баланса** работает напрямую с PostgreSQL через `psycopg2`
3. **Проверочный скрипт** тестирует все компоненты системы

Все изменения зафиксированы в git и отправлены в репозиторий! 🎉
