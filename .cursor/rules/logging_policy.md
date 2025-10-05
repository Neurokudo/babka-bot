# 📜 LOGGING POLICY

## 🎯 Цель
Поддерживать прозрачность всех операций биллинга.

### Правила:
- Любое списание монет → лог `[BILLING] charge_feature user_id=... cost=...`
- Любая ошибка YooKassa → лог `[PAYMENT ERROR] ...`
- Любое истечение подписки → лог `[SUBSCRIPTION] expired user_id=...`
- Любая попытка использования платной функции без подписки → лог `[ACCESS DENIED] user_id=... feature=...`

Cursor должен проверять, что все эти типы логов присутствуют в коде.

## 🔍 Обязательные логи

### 1. Операции с монетками
```python
# При списании монет
log.info(f"[BILLING] charge_feature user_id={user_id} cost={cost} feature={feature} success={success}")

# При начислении монет
log.info(f"[BILLING] add_coins user_id={user_id} amount={amount} reason={reason}")

# При возврате монет
log.info(f"[BILLING] refund user_id={user_id} amount={amount} reason={reason}")
```

### 2. Операции с подписками
```python
# При создании подписки
log.info(f"[SUBSCRIPTION] created user_id={user_id} plan={plan} coins={coins} expires={expires_at}")

# При истечении подписки
log.info(f"[SUBSCRIPTION] expired user_id={user_id} plan={plan}")

# При отмене подписки
log.info(f"[SUBSCRIPTION] cancelled user_id={user_id} plan={plan}")
```

### 3. Операции YooKassa
```python
# При успешном платеже
log.info(f"[PAYMENT] succeeded user_id={user_id} amount={amount} payment_id={payment_id}")

# При ошибке платежа
log.error(f"[PAYMENT ERROR] user_id={user_id} error={error} payment_id={payment_id}")

# При обработке webhook
log.info(f"[WEBHOOK] received event={event} payment_id={payment_id}")
```

### 4. Проверки доступа
```python
# При успешной проверке доступа
log.info(f"[ACCESS] granted user_id={user_id} feature={feature} balance={balance}")

# При отказе в доступе
log.warning(f"[ACCESS DENIED] user_id={user_id} feature={feature} reason={reason}")

# При попытке обхода проверок
log.error(f"[SECURITY] unauthorized_access_attempt user_id={user_id} feature={feature}")
```

### 5. Ошибки системы
```python
# При ошибке базы данных
log.error(f"[DB ERROR] operation={operation} user_id={user_id} error={error}")

# При ошибке внешнего API
log.error(f"[API ERROR] service={service} user_id={user_id} error={error}")

# При критических ошибках
log.critical(f"[CRITICAL] component={component} error={error} user_id={user_id}")
```

## 🚨 Критичные события для логирования

### События безопасности
- Попытки использования платных функций без подписки
- Попытки обхода проверок доступа
- Подозрительная активность с монетками
- Множественные неудачные попытки оплаты

### События бизнеса
- Покупка подписки
- Истечение подписки
- Отмена подписки
- Пополнение монеток
- Использование платных функций

### События системы
- Ошибки YooKassa
- Ошибки базы данных
- Ошибки внешних API
- Сбои в работе бота

## 📊 Формат логов

### Стандартный формат
```
[LEVEL] [COMPONENT] operation user_id={user_id} additional_data
```

### Примеры
```
[INFO] [BILLING] charge_feature user_id=12345 cost=3 feature=video_8s_audio success=True
[WARNING] [ACCESS DENIED] user_id=12345 feature=video_8s_audio reason=insufficient_coins
[ERROR] [PAYMENT ERROR] user_id=12345 error=invalid_payment_id payment_id=test_123
[INFO] [SUBSCRIPTION] created user_id=12345 plan=standard coins=100 expires=2024-11-04
```

## 🔍 Мониторинг логов

### Ключевые метрики для отслеживания:
- Количество успешных платежей
- Количество ошибок платежей
- Количество отказов в доступе
- Количество истекших подписок
- Количество списаний монеток

### Алерты для настройки:
- Более 10% ошибок платежей за час
- Более 5 попыток обхода доступа от одного пользователя
- Критические ошибки базы данных
- Сбои в работе YooKassa

## 📋 Чек-лист логирования

- [ ] Все операции с монетками логируются
- [ ] Все операции с подписками логируются
- [ ] Все операции YooKassa логируются
- [ ] Все проверки доступа логируются
- [ ] Все ошибки системы логируются
- [ ] Логи содержат достаточно информации для отладки
- [ ] Логи не содержат чувствительных данных (пароли, токены)
- [ ] Настроен мониторинг критичных событий

---

**Помните:** Логи — это глаза системы. Без качественного логирования невозможно отследить проблемы и обеспечить безопасность.
