# Новая UI система бота

## Обзор

Создана новая декларативная система управления интерфейсом бота, которая заменяет разрозненные функции клавиатур и обработчиков callback-ов.

## Структура

```
app/
├── ui/
│   ├── __init__.py          # Экспорт основных функций
│   ├── texts.py             # Централизованные тексты
│   ├── callbacks.py         # Система callback данных
│   ├── menu_schema.py       # Декларативная схема меню
│   ├── keyboards.py         # Генерация клавиатур
│   └── legacy_mapping.py    # Маппинг старых callback-ов
├── handlers/
│   ├── __init__.py          # Экспорт роутера
│   └── router.py            # Единый роутер callback-ов
scripts/
├── dump_flow.py             # Генерация диаграмм Mermaid
docs/                        # Автоматически генерируемая документация
test_ui_system.py           # Тесты системы
```

## Ключевые особенности

### ✅ Декларативная схема меню
- Все экраны и переходы описаны в `menu_schema.py`
- Легко добавлять новые экраны
- Автоматическая валидация схемы

### ✅ Централизованные тексты
- Все тексты в одном месте (`texts.py`)
- Готовность к интернационализации
- Форматирование с параметрами

### ✅ Структурированные callback данные
- Ограничение длины до 64 байт
- Валидация и логирование ошибок
- Обратная совместимость со старыми callback-ами

### ✅ Единый роутер
- Все callback-ы обрабатываются в одном месте
- Декораторы для регистрации хэндлеров
- Автоматический fallback к главному меню

### ✅ Автоматическая документация
- Генерация диаграмм Mermaid
- Анализ использования callback-ов
- Сводка по узлам меню

## Быстрый старт

### 1. Запуск тестов
```bash
python3 test_ui_system.py
```

### 2. Генерация документации
```bash
python3 scripts/dump_flow.py
```

### 3. Интеграция в main.py
```python
from app.handlers.router import register_router
from app.ui.keyboards import build_keyboard_with_description
from app.ui.texts import t

# В create_app() замените:
# app.add_handler(CallbackQueryHandler(on_cb))
register_router(app)  # Новый роутер

# Используйте новые функции клавиатур:
text, keyboard = build_keyboard_with_description("root")
```

## Основные компоненты

### Тексты (`texts.py`)
```python
from app.ui.texts import t

# Получение текста
text = t("menu.title")  # "🏠 Главное меню"

# С форматированием
text = t("desc.transforms", coins=100)  # "💰 У тебя: 100 монеток"
```

### Callback данные (`callbacks.py`)
```python
from app.ui.callbacks import Cb, Actions

# Создание callback
cb = Cb(Actions.NAV, "lego_menu")
callback_data = cb.pack()  # "nav|lego_menu"

# Парсинг callback
cb = parse_cb("nav|lego_menu")
print(cb.action)  # "nav"
print(cb.id)      # "lego_menu"
```

### Схема меню (`menu_schema.py`)
```python
MENU = {
    "root": {
        "text_key": "menu.title",
        "buttons": [
            {"text_key": "btn.generate", "to": "modes", "cb": ("make",)},
            {"text_key": "btn.lego", "to": "lego_menu", "cb": ("lego",)},
        ],
    },
    # ...
}
```

### Генерация клавиатур (`keyboards.py`)
```python
from app.ui.keyboards import build_keyboard_with_description

# Получить текст и клавиатуру
text, keyboard = build_keyboard_with_description("root")

# Только клавиатуру
keyboard = build_keyboard("modes")
```

### Роутер (`router.py`)
```python
from app.handlers.router import on_action

@on_action("custom_action")
async def handle_custom_action(call, cb):
    await call.message.edit_text("Обработка кастомного действия")
```

## Обратная совместимость

Система автоматически поддерживает старые callback-ы через маппинг в `legacy_mapping.py`:

```python
# Старый callback: "menu_make"
# Автоматически конвертируется в: Cb("make")

# Старый callback: "back_home" 
# Автоматически конвертируется в: Cb("nav", "root")
```

## Добавление новых экранов

### 1. Добавить тексты в `texts.py`
```python
"menu.new_screen": "Новый экран",
"btn.new_action": "Новое действие",
```

### 2. Добавить узел в `menu_schema.py`
```python
"new_screen": {
    "text_key": "menu.new_screen",
    "buttons": [
        {"text_key": "btn.new_action", "to": "new_screen", "cb": ("new_action",)},
        {"text_key": "btn.back", "to": "root", "cb": ("nav", "root")},
    ],
},
```

### 3. Зарегистрировать хэндлер в `router.py`
```python
@on_action("new_action")
async def handle_new_action(call, cb):
    await call.message.edit_text("Обработка нового действия")
```

## Тестирование

### Запуск тестов
```bash
python3 test_ui_system.py
```

### Валидация схемы
```python
from app.ui.menu_schema import validate_menu_schema
errors = validate_menu_schema()
print(errors)  # [] если все OK
```

### Проверка callback данных
```python
from app.ui.callbacks import parse_cb
cb = parse_cb("nav|root")
assert cb.action == "nav"
assert cb.id == "root"
```

## Документация

После запуска `python3 scripts/dump_flow.py` создаются файлы:

- `docs/flow.mmd` - основная диаграмма переходов
- `docs/flow_detailed.mmd` - подробная диаграмма с callback-ами
- `docs/callback_analysis.md` - анализ использования callback-ов
- `docs/node_summary.md` - сводка по узлам меню

## Миграция

### Постепенная миграция
```python
# В main.py добавьте миграционную обертку
from app.handlers.router import callback_entry

async def migrated_callback_handler(update, context):
    try:
        await callback_entry(update.callback_query)
    except Exception:
        await old_on_cb(update, context)  # Fallback

app.add_handler(CallbackQueryHandler(migrated_callback_handler))
```

### Полная миграция
```python
# Замените в create_app():
from app.handlers.router import register_router
register_router(app)  # Полная замена
```

## Преимущества новой системы

1. **Декларативность** - схема меню описана в одном месте
2. **Централизация** - все тексты и callback-ы в отдельных файлах
3. **Валидация** - автоматическая проверка корректности схемы
4. **Документация** - автоматическая генерация диаграмм
5. **Тестируемость** - полное покрытие тестами
6. **Обратная совместимость** - поддержка старых callback-ов
7. **Расширяемость** - легко добавлять новые экраны и действия
8. **Отладка** - логирование всех callback-ов и ошибок

## Troubleshooting

### Ошибка "Unknown action"
- Проверьте что хэндлер зарегистрирован через `@on_action`
- Убедитесь что действие есть в `Actions` классе

### Ошибка "Callback data too long"
- Система автоматически обрезает длинные callback-ы
- Проверьте логи на предупреждения

### Не отображается меню
- Проверьте что узел существует в `MENU`
- Убедитесь что `text_key` есть в `texts.py`

### Старые callback-ы не работают
- Проверьте маппинг в `legacy_mapping.py`
- Добавьте недостающие маппинги

## Контакты

При возникновении проблем:
1. Запустите тесты: `python3 test_ui_system.py`
2. Проверьте логи на ошибки
3. Валидируйте схему: `validate_menu_schema()`
4. Сгенерируйте документацию: `python3 scripts/dump_flow.py`
