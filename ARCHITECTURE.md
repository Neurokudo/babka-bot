# 🏗️ АРХИТЕКТУРА БОТА BABKA-BOT

## 📱 ГЛАВНОЕ МЕНЮ (`kb_home_inline`)

```
🏠 ГЛАВНОЕ МЕНЮ
├── 🎬 Создание видео → menu_make
├── 🧱 LEGO мультики → menu_lego  
├── 🖼️ Оживление изображения → menu_alive
├── 👗 Виртуальная примерочная → menu_tryon
├── 🧾 JSON (для продвинутых) → menu_jsonpro
├── 📚 Гайды / Оплата → menu_guides
└── 👤 Профиль / Баланс → menu_profile
```

---

## 🎬 СОЗДАНИЕ ВИДЕО (`menu_make`)

### 🔄 РЕЖИМЫ ГЕНЕРАЦИИ (`kb_modes`)
```
🎬 РЕЖИМЫ ВИДЕО
├── 🧠✨ Умный помощник → mode_helper
├── 🔮 Как у NEUROKUDO → mode_nkudo
├── ✏️ Я сам напишу промт → mode_manual
├── 🎲 Мемный режим → mode_meme
└── ⬅️ Назад в меню → back_home
```

### 🧠✨ УМНЫЙ ПОМОЩНИК (`mode_helper`)
```
📝 ВВОД ТЕКСТА → awaiting_scene
↓
🧠✨ УЛУЧШЕНИЕ → improve_scene()
↓
🎭 ВАРИАНТЫ (`kb_variants`)
├── 🔍 Усложни → var_complex
├── ✂️ Упрости → var_simple
├── 💬 Придумать фразу → generate_replica
├── ✍️ Ввести фразу вручную → manual_replica
├── 🔄 Заново → var_again
├── ➡️ Дальше → go_next
└── ⬅️ Назад → back_modes
```

### 🔮 NEUROKUDO (`mode_nkudo`)
```
🔮 NEUROKUDO МЕНЮ (`kb_nkudo_menu`)
├── 🔮 Создать как у Neurokudo → nkudo_single
├── 🎤 Репортаж из деревни → nkudo_reportage
└── ⬅️ Назад к режимам → back_modes

📺 ОДИНОЧНАЯ СЦЕНА (`kb_nkudo_single`)
├── 🔄 Другая сцена → nkudo_regenerate_single
├── 💬 Другая фраза → nkudo_embed_replica
├── 🧠✨ Улучшить помощником → nkudo_improve_single
├── ➡️ Далее к стилям → go_next
└── ⬅️ Назад → nkudo_menu_back

🎤 РЕПОРТАЖ (`kb_nkudo_reportage_edit`)
├── ✏️ Редактировать сцену 1 → edit_scene_1
├── ✏️ Редактировать сцену 2 → edit_scene_2
├── ➡️ Далее к стилям → go_next
└── ⬅️ Назад → nkudo_menu_back
```

### ✏️ РУЧНОЙ РЕЖИМ (`mode_manual`)
```
📝 ВВОД ТЕКСТА → awaiting_scene
↓
📝 ПРОМТ ПРИНЯТ → kb_variants
└── [Те же кнопки что и в помощнике]
```

### 🎲 МЕМНЫЙ РЕЖИМ (`mode_meme`)
```
🎲 СЛУЧАЙНАЯ СЦЕНА → random_meme_scene()
↓
🎭 МЕМНЫЕ ВАРИАНТЫ (`kb_meme`)
├── 🎲 Крутить ещё → meme_again
├── 🧠✨ Улучшить с помощником → meme_to_helper
├── ➡️ Дальше → go_next
└── ⬅️ Назад → back_modes
```

---

## 🎨 СТИЛИ И НАСТРОЙКИ

### 🎨 ВЫБОР СТИЛЕЙ (`kb_styles`)
```
🎨 СТИЛИ
├── 🎬 Кино → style_Кино
├── 🎭 Аниме → style_Аниме
├── 🎨 Художественный → style_Художественный
├── 🏞️ Документальный → style_Документальный
├── ⏩ Без стиля – далее → style_None
└── ⬅️ Назад → back_modes
```

### 📱 ВЫБОР ОРИЕНТАЦИИ (`kb_orientation`)
```
📱 ОРИЕНТАЦИЯ
├── 📱 Вертикальное (9:16) → ori_916
└── 🖥 Горизонтальное (16:9) → ori_169
```

### 🎵 ВЫБОР АУДИО (`kb_audio_choice`)
```
🎵 АУДИО
├── 🔊 С аудио (дороже) → audio_on
└── 🔇 Без аудио (дешевле) → audio_off
```

### 🚀 ФИНАЛЬНОЕ МЕНЮ
```
📝 ИТОГОВЫЕ НАСТРОЙКИ
├── 🚀 Создать видео → generate_now
├── ✍️ Изменить сцену → prompt_add
└── 🔄 Переделать → go_next
```

---

## 🧱 LEGO МУЛЬТИКИ (`menu_lego`)

### 🧱 LEGO МЕНЮ (`kb_lego_menu`)
```
🧱 LEGO МЕНЮ
├── 🧱 LEGO сцена → lego_single
├── 🎤 LEGO репортаж → lego_reportage
└── ⬅️ Назад к режимам → back_modes
```

### 🧱 LEGO СЦЕНА (`kb_lego_single`)
```
🧱 LEGO СЦЕНА
├── 🔄 Другая сцена → lego_regenerate_single
├── 💬 Другая фраза → lego_embed_replica
├── 🧠✨ Улучшить помощником → lego_improve_single
├── ➡️ Далее к ориентации → go_orientation
└── ⬅️ Назад → lego_menu_back
```

---

## 🖼️ ОЖИВЛЕНИЕ ИЗОБРАЖЕНИЯ (`menu_alive`)

```
🖼️ ОЖИВЛЕНИЕ
├── 📸 Загрузить фото → awaiting_image
├── ✏️ Описать изменения → awaiting_prompt
└── ⬅️ Назад → back_home
```

---

## 👗 ВИРТУАЛЬНАЯ ПРИМЕРОЧНАЯ (`menu_tryon`)

### 🎯 НАЧАЛО ПРИМЕРОЧНОЙ (`kb_tryon_start`)
```
👗 ПРИМЕРОЧНАЯ
├── 👤 Примерить на себя → tryon_start
└── ⬅️ Назад → back_home
```

### 👤 ЭТАПЫ ПРИМЕРОЧНОЙ
```
👤 ЭТАПЫ
├── 📸 Фото человека → awaiting_person
├── 👕 Фото одежды → awaiting_garment
├── ✅ Подтверждение → confirm
├── 🎨 Результат → after
└── ✏️ Описать изменения → awaiting_prompt
```

### 🔧 КНОПКИ ПРИМЕРОЧНОЙ
```
🎯 ПРИМЕРОЧНАЯ КНОПКИ
├── kb_tryon_need_garment → Нужна одежда
├── kb_tryon_confirm → Подтвердить
├── kb_tryon_after → После примерки
└── kb_tryon_start → Начать
```

---

## 🧾 JSON ДЛЯ ПРОДВИНУТЫХ (`menu_jsonpro`)

### 🧾 JSON МЕНЮ (`kb_jsonpro_start`)
```
🧾 JSON
├── 📝 Ввести текст → awaiting_text
└── ⬅️ Назад → back_home
```

### 📝 JSON ПОСЛЕ ТЕКСТА (`kb_jsonpro_after_text`)
```
📝 JSON РЕЗУЛЬТАТ
├── 🔄 Изменить ориентацию → jsonpro_orientation
├── 🚀 Создать видео → jsonpro_generate
└── ⬅️ Назад → jsonpro_back
```

---

## 🎬 ГЕНЕРАЦИЯ ВИДЕО

### 🎬 ТИПЫ ГЕНЕРАЦИИ
```
🎬 ГЕНЕРАЦИЯ
├── 🎭 Обычные режимы → generate_video_sync()
├── 🎤 Репортаж (2 видео) → generate_video_sync() × 2
└── 🧾 JSON режим → generate_video_sync()
```

### 🎥 ПОСЛЕ ВИДЕО (`kb_after_video`)
```
🎥 РЕЗУЛЬТАТ
├── 🔄 Создать ещё → back_to_modes
├── 📤 Поделиться → share_video
├── 💾 Сохранить → save_video
└── ⬅️ Главное меню → back_home
```

---

## 💰 МОНЕТИЗАЦИЯ

### 💰 ПРОФИЛЬ (`menu_profile`)
```
👤 ПРОФИЛЬ
├── 💰 Баланс → show_balance
├── 🎫 Купить монеты → buy_coins
├── 📊 Статистика → show_stats
└── ⬅️ Назад → back_home
```

### 📚 ГАЙДЫ (`menu_guides`)
```
📚 ГАЙДЫ
├── 📖 Как пользоваться → show_guide
├── 💳 Способы оплаты → show_payment
├── ❓ FAQ → show_faq
└── ⬅️ Назад → back_home
```

---

## 🔧 ТЕХНИЧЕСКИЕ КНОПКИ

### 🔄 НАВИГАЦИЯ
```
🔄 НАВИГАЦИЯ
├── ⬅️ Назад → back_*
├── ➡️ Далее → go_*
├── 🏠 Главное меню → back_home
└── 🔄 Переделать → go_next
```

### ⚙️ СИСТЕМНЫЕ
```
⚙️ СИСТЕМНЫЕ
├── 🆘 SOS → support_request
├── 📊 Статистика → admin_stats
└── 🔧 Настройки → admin_settings
```

---

## 📊 СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ

### 🗂️ ОСНОВНЫЕ ПОЛЯ
```python
user_state = {
    "mode": "helper|manual|nkudo|lego|meme",
    "scene": "текст сцены",
    "style": "название стиля",
    "replica": "фраза героя",
    "orientation": "9:16|16:9",
    "with_audio": True|False,
    "awaiting_scene": True|False,
    "source_text": "исходный текст",
    "nkudo_type": "single|reportage",
    "nkudo_scene1": "сцена 1",
    "nkudo_scene2": "сцена 2",
    "tryon": {...},
    "jsonpro": {...}
}
```

---

## 🎯 ПОТОКИ РАБОТЫ

### 📱 ОСНОВНОЙ ПОТОК
```
Главное меню → Создание видео → Режим → Сцена → Стиль → Ориентация → Аудио → Генерация
```

### 🧱 LEGO ПОТОК
```
Главное меню → LEGO мультики → Тип → Сцена → Ориентация → Генерация
```

### 👗 ПРИМЕРОЧНАЯ ПОТОК
```
Главное меню → Примерочная → Фото человека → Фото одежды → Результат
```

### 🧾 JSON ПОТОК
```
Главное меню → JSON → Ввод текста → Ориентация → Генерация
```

---

## 🎨 СТИЛИ ВИДЕО

### 🎬 ДОСТУПНЫЕ СТИЛИ
- **🎬 Кино** - кинематографический стиль
- **🎭 Аниме** - аниме стиль
- **🎨 Художественный** - художественный стиль
- **🏞️ Документальный** - документальный стиль
- **⏩ Без стиля** - без дополнительной стилизации

---

## 🔧 ИНТЕГРАЦИИ

### 🤖 ВНЕШНИЕ СЕРВИСЫ
- **OpenAI GPT** - улучшение сцен и генерация фраз
- **Google Veo 3** - генерация видео
- **Google Imagen** - виртуальная примерочная
- **Google Gemini** - обработка изображений

### 📊 МОНЕТИЗАЦИЯ
- **Telegram Payments** - покупка монет
- **Баланс пользователя** - система монет
- **Тарифы** - разные цены для разных режимов

---

## 🚀 ДЕПЛОЙ

### 🌐 ПЛАТФОРМЫ
- **Railway** - основная платформа
- **Render** - резервная платформа
- **GitHub** - исходный код

### 📁 ФАЙЛЫ
- `main.py` - основной бот
- `veo_client.py` - клиент для Veo 3
- `tryon_client.py` - клиент для примерочной
- `nano_client.py` - клиент для Gemini
- `requirements.txt` - зависимости
- `railway.json` - конфигурация Railway
- `render.yaml` - конфигурация Render
