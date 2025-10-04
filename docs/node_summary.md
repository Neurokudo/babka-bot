# Сводка узлов меню

## root
**Название:** 🏠 Главное меню
**Кнопок:** 9
**Кнопки:**
- 🎬 Генерировать видео → modes (make)
- 🧱 LEGO мультики → lego_menu (lego)
- 🖼️ Оживить фото → root (alive)
- 👗 Примерочная → tryon_start (tryon)
- 📸 Изменить фото → transforms (transforms)
- ⚡ JSON Pro → jsonpro_start (jsonpro)
- 📚 Гайды → root (guides)
- 👤 Профиль → profile (profile)
- 📜 История → root (history)

## modes
**Название:** Выберите режим генерации:
**Кнопок:** 5
**Кнопки:**
- 🤖 С помощником → modes (helper)
- ✋ Вручную → modes (manual)
- 😄 Мем → modes (meme)
- 🎭 НКУДО → nkudo_menu (nkudo)
- ⬅️ Назад → root (back_modes)

## lego_menu
**Название:** 🧱 Режим «LEGO мультики» активирован!
**Описание:** Режим для создания LEGO мультиков: генерируем сцены в стиле LEGO с автоматическим стилем!

Выберите тип сюжета:
**Кнопок:** 3
**Кнопки:**
- 🎬 Одна сцена → lego_single (lego_single)
- 📰 Репортаж → lego_reportage (lego_reportage)
- ⬅️ Назад в меню → root (lego_menu_back)

## lego_single
**Название:** 🎬 Одна сцена
**Кнопок:** 4
**Кнопки:**
- 🔄 Перегенерировать → lego_single (lego_regenerate)
- ✨ Улучшить → lego_single (lego_improve)
- lego.embed_replica → lego_single (lego_embed_replica)
- ⬅️ Назад → lego_menu (nav)

## lego_reportage
**Название:** 📰 Репортаж
**Кнопок:** 1
**Кнопки:**
- ⬅️ Назад → lego_menu (nav)

## nkudo_menu
**Название:** 🎭 НКУДО
**Кнопок:** 3
**Кнопки:**
- 🎬 Одна сцена → nkudo_single (nkudo_single)
- 📰 Репортаж → nkudo_reportage (nkudo_reportage)
- ⬅️ Назад в меню → modes (nkudo_menu_back)

## nkudo_single
**Название:** 🎬 Одна сцена
**Кнопок:** 4
**Кнопки:**
- 🔄 Перегенерировать → nkudo_single (nkudo_regenerate)
- ✨ Улучшить → nkudo_single (nkudo_improve)
- nkudo.embed_replica → nkudo_single (nkudo_embed_replica)
- ⬅️ Назад → nkudo_menu (nav)

## nkudo_reportage
**Название:** 📰 Репортаж
**Кнопок:** 8
**Кнопки:**
- 🎲 Крутить сцену 1 → nkudo_reportage (nkudo_reroll_scene1)
- 🎲 Крутить сцену 2 → nkudo_reportage (nkudo_reroll_scene2)
- ✏️ Изменить сцену 1 → nkudo_reportage (nkudo_edit_scene1)
- ✏️ Изменить сцену 2 → nkudo_reportage (nkudo_edit_scene2)
- 🔄 Всё заново → nkudo_reportage (nkudo_regenerate_report)
- 🧠✨ Улучшить помощником → nkudo_reportage (nkudo_improve_report)
- ➡️ Далее к генерации → nkudo_reportage (nkudo_approve)
- ⬅️ Назад → nkudo_menu (nav)

## tryon_start
**Название:** 👗 Виртуальная примерочная
**Описание:** 1) Пришлите фото человека, которого будем одевать
2) Затем пришлите фото одежды (можно даже на другом человеке)
**Кнопок:** 2
**Кнопки:**
- Начать примерку → tryon_start (tryon_start)
- ⬅️ Назад → root (nav)

## tryon_confirm
**Название:** ✅ Готово
**Кнопок:** 2
**Кнопки:**
- ✅ Готово → tryon_confirm (tryon_confirm)
- ⬅️ Назад → tryon_start (nav)

## tryon_after
**Название:** tryon.after
**Кнопок:** 7
**Кнопки:**
- 🔄 Поменять местами → tryon_after (tryon_swap)
- 🔄 Заново → tryon_after (tryon_reset)
- 🔄 Новая поза → tryon_after (tryon_new_pose)
- 🔄 Новая одежда → tryon_after (tryon_new_garment)
- 🔄 Новый фон → tryon_after (tryon_new_bg)
- 💬 Улучшить промпт → tryon_after (tryon_prompt)
- ⬅️ Назад → root (nav)

## transforms
**Название:** 📸 Изменить фото
**Описание:** 💰 У тебя: {coins} монеток

✨ Удалить фон (−1 монетка)
Вырежу фон. Могу поставить белый/градиент/ваш фон.

👥 Совместить людей (−1 монетка)
Соберу всех в один кадр, как будто снимались вместе.

🧩 Внедрить объект на фото (−1 монетка)
Добавлю предмет и впишу по свету/перспективе.

🪄 Магическая ретушь (−1 монетка)
Уберу лишнее или добавлю деталь. Можно указать область.

📷 Polaroid (−1 монетка)
Рамка, плёночное зерно, подпись.
**Кнопок:** 6
**Кнопки:**
- ✨ Удалить фон → transforms (transform_remove_bg)
- 👥 Совместить людей → transforms (transform_merge_people)
- 🧩 Внедрить объект на фото → transforms (transform_inject_object)
- 🪄 Магическая ретушь → transforms (transform_retouch)
- 📷 Polaroid → transforms (transform_polaroid)
- ⬅️ Назад → root (nav)

## transform_quality
**Название:** transform.quality
**Кнопок:** 3
**Кнопки:**
- ⚡ Базовая → transform_quality (quality_basic)
- 💎 Премиум → transform_quality (quality_premium)
- ⬅️ Назад → transforms (nav)

## jsonpro_start
**Название:** JSON Pro режим
**Кнопок:** 2
**Кнопки:**
- Введите JSON → jsonpro_start (jsonpro_enter)
- ⬅️ Назад → root (nav)

## jsonpro_orientation
**Название:** jsonpro.orientation
**Кнопок:** 4
**Кнопки:**
- 📱 9:16 → jsonpro_orientation (jsonpro_ori_916)
- 🖥️ 16:9 → jsonpro_orientation (jsonpro_ori_169)
- 🚀 Генерировать → jsonpro_orientation (jsonpro_generate)
- ⬅️ Назад → jsonpro_start (nav)

## profile
**Название:** 👤 Профиль / Баланс 💰
**Кнопок:** 7
**Кнопки:**
- 📋 Тарифы → profile (show_plans)
- 💰 Монетки → profile (show_topup)
- 🔄 Сменить тариф → profile (change_plan)
- 📜 История платежей → profile (show_history)
- 📄 Условия → profile (show_terms)
- 💬 Поддержка → profile (contact_support)
- ⬅️ Назад → root (nav)

## styles
**Название:** style.choose
**Кнопок:** 3
**Кнопки:**
- 🇯🇵 Анимэ → styles (style_anime)
- 🧱 LEGO → styles (style_lego)
- ⏩ Без стиля – далее → styles (style_none)

## orientation
**Название:** orientation.choose
**Кнопок:** 2
**Кнопки:**
- 📱 Портрет (9:16) → orientation (ori_916)
- 🖥️ Альбом (16:9) → orientation (ori_169)

## scene_edit
**Название:** scene.edit
**Кнопок:** 2
**Кнопки:**
- ✅ Сохранить → scene_edit (scene_save)
- ❌ Отмена → scene_edit (scene_cancel)

## meme
**Название:** 😄 Мем
**Кнопок:** 3
**Кнопки:**
- meme.again → meme (meme_again)
- meme.to_helper → meme (meme_to_helper)
- ⬅️ Назад → modes (nav)

## video_result
**Название:** video.result
**Кнопок:** 2
**Кнопки:**
- 🔄 Повторить → video_result (video_retry)
- ⬅️ Назад → root (nav)

## transform_result
**Название:** transform.result
**Кнопок:** 2
**Кнопки:**
- 🔄 Повторить → transform_result (transform_retry)
- ⬅️ Назад → transforms (nav)

## low_coins_warning
**Название:** 💰 Недостаточно монеток
**Кнопок:** 2
**Кнопки:**
- ⏭️ Продолжить несмотря на низкий баланс → low_coins_warning (skip_low_coins)
- 💰 Монетки → low_coins_warning (show_topup)
