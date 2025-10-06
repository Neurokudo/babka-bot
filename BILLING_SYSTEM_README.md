# 🏦 Централизованная система биллинга и аудита

## 🎯 Обзор

Полностью централизованная система управления балансом с автоматическим аудитом всех операций с монетами. Каждая транзакция логируется, отслеживается и может быть проанализирована.

## 🏗️ Архитектура

```
app/
├── services/
│   ├── balance_manager.py      # Централизованное управление балансом
│   ├── billing_observer.py     # Аудит и отчеты
│   └── pricing.py              # Тарифы и описания фич
├── db/
│   ├── db_subscriptions.py     # Низкоуровневая работа с балансом
│   └── db_billing_audit.py     # Журнал всех операций
└── handlers/
    ├── router.py               # Основные хэндлеры
    └── admin_router.py         # Админские команды
```

## 🔧 Основные компоненты

### 1. Balance Manager (`balance_manager.py`)

Единая точка управления всеми операциями с монетами:

```python
from app.services import balance_manager

# Получить баланс
balance = balance_manager.get_balance(user_id)

# Добавить монеты
new_balance = balance_manager.add_coins(
    user_id=user_id,
    amount=100,
    reason="Subscription payment",
    feature="subscription_lite"
)

# Потратить монеты
new_balance = balance_manager.spend_coins(
    user_id=user_id,
    amount=20,
    reason="Video generation",
    feature="video_8s_audio"
)

# Установить точный баланс (админ)
balance_manager.set_balance(
    user_id=user_id,
    new_balance=500,
    reason="Admin correction",
    admin_note="Fixed incorrect balance"
)
```

### 2. Billing Observer (`billing_observer.py`)

Автоматическое логирование и отчетность:

```python
from app.services import billing_observer

# Получить историю пользователя
history = billing_observer.get_user_recent_transactions(user_id, limit=10)

# Ежедневный отчет
daily_report = billing_observer.get_daily_report()

# Недельный отчет
weekly_report = billing_observer.get_weekly_report()

# Месячный отчет
monthly_report = billing_observer.get_monthly_report()

# Статистика по функции
feature_stats = billing_observer.get_feature_statistics("video_8s_audio", days=30)
```

### 3. Audit Database (`db_billing_audit.py`)

Таблица `billing_audit` для хранения всех операций:

```sql
CREATE TABLE billing_audit (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    delta INTEGER NOT NULL,           -- Изменение баланса (+/-)
    feature TEXT,                     -- Тип функции
    reason TEXT,                      -- Причина операции
    old_balance INTEGER,              -- Баланс до операции
    new_balance INTEGER,              -- Баланс после операции
    timestamp TIMESTAMP DEFAULT NOW()
);
```

## 🎮 Админские команды

### Управление балансом

- `/balance <user_id>` - показать баланс и транзакции
- `/set_balance <user_id> <new_balance> [reason]` - установить баланс
- `/add_coins <user_id> <amount> <reason>` - добавить монеты
- `/spend_coins <user_id> <amount> <reason>` - списать монеты

### Отчеты и аудит

- `/billing_report [daily|weekly|monthly]` - отчет по биллингу
- `/audit <user_id> [limit]` - детальная история пользователя
- `/help_admin` - справка по админским командам

## 📊 Система отчетов

### Ежедневный отчет
```
📅 Ежедневный отчёт BabkaBot (2025-01-06)
💸 Списаний за сутки: 254 монет
💰 Начислений за сутки: 1200 монет
👥 Уникальных пользователей: 33
🔥 Топ функций:
   1. video_8s_audio — 123 монет (45 использований)
   2. virtual_tryon — 66 монет (22 использования)
   3. image_basic — 42 монеты (42 использования)
```

### Недельный/месячный отчет
Аналогичный формат с данными за период.

## 🚀 Установка и настройка

### 1. Инициализация таблицы аудита

```bash
python scripts/init_billing_audit.py
```

### 2. Миграция существующих операций

```bash
python scripts/migrate_to_balance_manager.py
```

### 3. Тестирование системы

```bash
python scripts/test_billing_system.py
```

### 4. Генерация ежедневного отчета

```bash
python scripts/daily_report.py
```

## 🔄 Миграция существующего кода

### Было:
```python
from app.db import db_subscriptions as db
db.update_user_balance(user_id, -20)
```

### Стало:
```python
from app.services import balance_manager
balance_manager.spend_coins(
    user_id=user_id,
    amount=20,
    reason="Video generation",
    feature="video_8s_audio"
)
```

## 📈 Мониторинг и аналитика

### Автоматическое логирование
Каждая операция автоматически логируется:
```
[AUDIT] 5015100177 | Δ=-20 | video_8s_audio | 100→80 | Video generation
[BALANCE -] uid=5015100177 -20 → 80 (Video generation)
```

### Отслеживание метрик
- Общий оборот монет
- Популярность функций
- Активность пользователей
- Эффективность пополнений

## 🛡️ Безопасность

### Проверки
- Валидация сумм (только положительные)
- Проверка достаточности средств
- Логирование всех админских операций

### Аудит
- Полная история всех операций
- Невозможность удаления записей
- Отслеживание изменений баланса

## 🔧 Настройка админов

В `app/handlers/admin_router.py`:

```python
ADMIN_IDS = [5015100177, 123456789]  # Добавьте ID администраторов
```

## 📋 Критерии завершенности

✅ Все монетные операции проходят через `balance_manager`  
✅ Каждая операция автоматически логируется в `billing_audit`  
✅ У каждой операции есть `feature` и `reason`  
✅ Админские команды работают корректно  
✅ Система отчетов функционирует  
✅ Миграция существующего кода завершена  
✅ Тесты проходят успешно  

## 🎉 Результат

Теперь у вас есть полноценная система управления балансом с:
- Централизованным управлением монетами
- Автоматическим аудитом всех операций
- Детальными отчетами и аналитикой
- Админскими инструментами
- Полной прозрачностью финансовых операций

Система готова к продакшену! 🚀
