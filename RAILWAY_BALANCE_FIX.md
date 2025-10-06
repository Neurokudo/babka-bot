# Исправление баланса в Railway

## Проблема
Баланс пользователя 5015100177 не изменился, потому что локальный скрипт работал с SQLite, а бот на Railway использует PostgreSQL.

## Решение

### Вариант 1: Через Railway Shell (рекомендуется)

1. Зайдите в Railway → ваш сервис → Shell
2. Выполните команду:

```bash
python - <<'PY'
import os
os.environ.get("DATABASE_URL") or print("⚠️ DATABASE_URL not set in this shell")

from app.db import db_subscriptions as db
UID = 5015100177

cur = db.get_user_balance(UID)
delta = 100 - cur
ok = db.update_user_balance(UID, delta, note=f"Admin set balance to 100 (was {cur})")
new_bal = db.get_user_balance(UID)

print({"ok": ok, "old": cur, "delta": delta, "new": new_bal})
PY
```

**Ожидаемый вывод:**
```json
{"ok": true, "old": 1625, "delta": -1525, "new": 100}
```

### Вариант 2: Прямой SQL (если Вариант 1 не сработал)

```bash
python - <<'PY'
import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("UPDATE users SET coins = 100 WHERE user_id = %s", (5015100177,))
cur.execute("""
  INSERT INTO transactions(user_id, feature, coins_spent, note)
  VALUES (%s,'balance_update',0,'Admin set balance to 100')
""", (5015100177,))
conn.commit()
cur.close(); conn.close()
print("✅ balance set to 100")
PY
```

## Проверка

После выполнения команды в логах бота должно появиться:
```
Loaded user 5015100177 from DB: coins=100, plan=standard
```

## Что исправлено

1. ✅ Добавлен legacy shim для старого коллбека `show_tariffs`
2. ✅ Кнопка "Тарифы" теперь перенаправляется на новый хэндлер
3. ✅ Ошибка "cannot access local variable 'check_subscription'" устранена
4. 🔄 Баланс нужно исправить в Railway (инструкция выше)

## Тестирование

После исправления баланса:
1. Нажмите "Профиль" → должно показать "Монет: 100"
2. Нажмите "Тарифы" → должен открыться список без ошибок
3. Выполните любую операцию за 1 монету → баланс станет 99
