# Руководство по миграции UI системы

## Обзор изменений

Создана новая декларативная система меню и обработки callback-ов, которая заменяет разрозненные функции клавиатур и обработчиков в main.py.

## Новые файлы

- `app/ui/texts.py` - централизованные тексты
- `app/ui/callbacks.py` - система callback данных
- `app/ui/menu_schema.py` - декларативная схема меню
- `app/ui/keyboards.py` - генерация клавиатур
- `app/handlers/router.py` - единый роутер callback-ов
- `scripts/dump_flow.py` - генерация диаграмм Mermaid
- `test_ui_system.py` - тесты новой системы

## Пошаговая миграция

### Шаг 1: Подготовка

1. Убедитесь что все новые файлы созданы
2. Запустите тесты: `python3 test_ui_system.py`
3. Сгенерируйте документацию: `python3 scripts/dump_flow.py`

### Шаг 2: Замена обработчика callback-ов

В `main.py` замените:

```python
# СТАРЫЙ КОД
app.add_handler(CallbackQueryHandler(on_cb))

# НОВЫЙ КОД
from app.handlers.router import register_router
register_router(app)
```

Или используйте миграционную обертку:

```python
from app.handlers.router import callback_entry

async def migrated_on_cb(update, context):
    try:
        await callback_entry(update.callback_query)
    except Exception as e:
        # Fallback к старому обработчику
        await on_cb(update, context)

app.add_handler(CallbackQueryHandler(migrated_on_cb))
```

### Шаг 3: Замена функций клавиатур

Замените старые функции клавиатур на новые:

```python
# СТАРЫЙ КОД
def kb_home_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Генерировать видео", callback_data="menu_make")],
        # ... остальные кнопки
    ])

# НОВЫЙ КОД
from app.ui.keyboards import build_keyboard_with_description

def kb_home_inline():
    _, keyboard = build_keyboard_with_description("root")
    return keyboard
```

### Шаг 4: Замена текстов

Используйте централизованные тексты:

```python
# СТАРЫЙ КОД
await message.reply_text("🏠 Главное меню", reply_markup=keyboard)

# НОВЫЙ КОД
from app.ui.texts import t
await message.reply_text(t("menu.title"), reply_markup=keyboard)
```

### Шаг 5: Обновление callback данных

Замените создание callback данных:

```python
# СТАРЫЙ КОД
callback_data = "menu_make"

# НОВЫЙ КОД
from app.ui.callbacks import Cb, Actions
callback_data = Cb(Actions.MENU_MAKE).pack()
```

## Маппинг старых callback-ов на новые

| Старый callback | Новый action | ID | Extra |
|----------------|--------------|----|-------| 
| `menu_make` | `make` | - | - |
| `menu_lego` | `lego` | - | - |
| `menu_tryon` | `tryon` | - | - |
| `menu_transforms` | `transforms` | - | - |
| `back_home` | `nav` | `root` | - |
| `nkudo_single` | `nkudo_single` | - | - |
| `lego_single` | `lego_single` | - | - |

## Обратная совместимость

Для обеспечения обратной совместимости добавьте маппинг старых callback-ов:

```python
# В app/handlers/router.py добавьте:
OLD_CALLBACK_MAP = {
    "menu_make": Actions.MENU_MAKE,
    "menu_lego": Actions.MENU_LEGO,
    "menu_tryon": Actions.MENU_TRYON,
    "menu_transforms": Actions.MENU_TRANSFORMS,
    "back_home": (Actions.NAV, "root"),
    # ... остальные маппинги
}

@router.callback_query()
async def callback_entry_with_fallback(call: types.CallbackQuery):
    cb = parse_cb(call.data or "")
    
    # Если новый формат не распарсился, пробуем старый
    if not cb and call.data in OLD_CALLBACK_MAP:
        mapping = OLD_CALLBACK_MAP[call.data]
        if isinstance(mapping, tuple):
            cb = Cb(*mapping)
        else:
            cb = Cb(mapping)
    
    if cb and cb.action in HANDLERS:
        await HANDLERS[cb.action](call, cb)
    else:
        await show_error_and_menu(call, "error.button_outdated")
```

## Тестирование

1. Запустите тесты: `python3 test_ui_system.py`
2. Проверьте генерацию диаграмм: `python3 scripts/dump_flow.py`
3. Протестируйте бота с новыми callback-ами
4. Убедитесь что старые callback-ы работают через fallback

## Откат

Если нужно откатить изменения:

1. Верните старый обработчик callback-ов
2. Верните старые функции клавиатур
3. Удалите импорты новых модулей

## Дальнейшее развитие

1. Добавляйте новые узлы в `menu_schema.py`
2. Регистрируйте новые хэндлеры через `@on_action`
3. Обновляйте тексты в `texts.py`
4. Регенерируйте документацию при изменениях

## Полезные команды

```bash
# Запуск тестов
python3 test_ui_system.py

# Генерация документации
python3 scripts/dump_flow.py

# Валидация схемы
python3 -c "from app.ui.menu_schema import validate_menu_schema; print(validate_menu_schema())"

# Просмотр всех callback действий
python3 -c "from app.handlers.router import HANDLERS; print(list(HANDLERS.keys()))"
```
