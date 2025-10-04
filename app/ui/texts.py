# app/ui/texts.py
"""Централизованные тексты для интерфейса бота"""

T = {
    "ru": {
        # Главное меню
        "menu.title": "🏠 Главное меню",
        "menu.generate": "Выберите режим генерации:",
        "menu.lego": "🧱 Режим «LEGO мультики» активирован!",
        "menu.alive": "🖼️ Оживление изображения (в разработке).",
        "menu.tryon": "👗 Виртуальная примерочная",
        "menu.transforms": "📸 Изменить фото",
        "menu.jsonpro": "JSON Pro режим",
        "menu.guides": "📚 Гайды",
        "menu.profile": "👤 Профиль / Оплата 💰",
        
        # Кнопки главного меню
        "btn.generate": "🎬 Генерировать видео",
        "btn.lego": "🧱 LEGO мультики",
        "btn.alive": "🖼️ Оживить фото",
        "btn.tryon": "👗 Примерочная",
        "btn.transforms": "📸 Изменить фото",
        "btn.jsonpro": "⚡ JSON Pro",
        "btn.guides": "📚 Гайды / Инструкции",
        "btn.profile": "👤 Профиль / Баланс",
        "btn.history": "📜 История",
        "btn.back": "⬅️ Назад",
        "btn.home": "🏠 Главное меню",
        "btn.cancel": "❌ Отмена",
        "btn.save": "✅ Сохранить",
        "btn.continue": "➡️ Далее",
        "btn.retry": "🔄 Повторить",
        "btn.generate_now": "🚀 Генерировать сейчас",
        "btn.skip": "⏭️ Пропустить",
        
        # Режимы генерации
        "mode.helper": "🤖 С помощником",
        "mode.manual": "✋ Вручную",
        "mode.meme": "😄 Мем",
        "mode.nkudo": "🎭 НКУДО",
        
        # LEGO режим
        "lego.single": "🎬 Одна сцена",
        "lego.reportage": "📰 Репортаж",
        "lego.menu_back": "⬅️ Назад в меню",
        "lego.regenerate": "🔄 Перегенерировать",
        "lego.improve": "✨ Улучшить",
        "lego.keep": "✅ Оставить",
        "lego.cancel": "❌ Отменить",
        "lego.again": "🔄 Ещё раз",
        
        # НКУДО режим
        "nkudo.single": "🎬 Одна сцена",
        "nkudo.reportage": "📰 Репортаж",
        "nkudo.menu_back": "⬅️ Назад в меню",
        "nkudo.regenerate": "🔄 Перегенерировать",
        "nkudo.improve": "✨ Улучшить",
        "nkudo.keep": "✅ Оставить",
        "nkudo.cancel": "❌ Отменить",
        "nkudo.approve": "➡️ Далее к генерации",
        "nkudo.reroll_scene1": "🎲 Крутить сцену 1",
        "nkudo.reroll_scene2": "🎲 Крутить сцену 2",
        "nkudo.edit_scene1": "✏️ Изменить сцену 1",
        "nkudo.edit_scene2": "✏️ Изменить сцену 2",
        "nkudo.regenerate_report": "🔄 Всё заново",
        "nkudo.improve_report": "🧠✨ Улучшить помощником",
        
        # Трансформации
        "transform.remove_bg": "✨ Удалить фон",
        "transform.merge_people": "👥 Совместить людей",
        "transform.inject_object": "🧩 Внедрить объект на фото",
        "transform.retouch": "🪄 Магическая ретушь",
        "transform.polaroid": "📷 Polaroid",
        "transform.quality_basic": "⚡ Базовая",
        "transform.quality_premium": "💎 Премиум",
        
        # Примерочная
        "tryon.start": "Начать примерку",
        "tryon.swap": "🔄 Поменять местами",
        "tryon.reset": "🔄 Заново",
        "tryon.confirm": "✅ Готово",
        "tryon.new_pose": "🔄 Новая поза",
        "tryon.new_garment": "🔄 Новая одежда",
        "tryon.new_bg": "🔄 Новый фон",
        "tryon.prompt": "💬 Улучшить промпт",
        
        # Стили
        "style.anime": "🇯🇵 Анимэ",
        "style.lego": "🧱 LEGO",
        "style.none": "⏩ Без стиля – далее",
        
        # Ориентация
        "orientation.portrait": "📱 Портрет (9:16)",
        "orientation.landscape": "🖥️ Альбом (16:9)",
        
        # JSON Pro
        "jsonpro.enter": "Введите JSON",
        "jsonpro.ori_916": "📱 9:16",
        "jsonpro.ori_169": "🖥️ 16:9",
        "jsonpro.generate": "🚀 Генерировать",
        
        # Платежи и тарифы
        "payment.plans": "📋 Тарифы",
        "payment.topup": "💰 Монетки",
        "payment.terms": "📄 Условия",
        "payment.support": "💬 Поддержка",
        "payment.change_plan": "🔄 Сменить тариф",
        "payment.show_history": "📜 История платежей",
        "payment.quick_topup": "⚡ Быстрые докупки",
        
        # Профиль
        "profile.title": "👤 Профиль",
        "profile.balance": "💰 Осталось: {coins} монеток",
        "profile.tariff": "📊 Тариф: {tariff_name}",
        "profile.video_count": "🎬 Видео: {count}",
        "profile.photo_count": "📸 Фотографий: {count}",
        "profile.cost_examples": "💡 Стоимость генераций обновляется автоматически",
        
        # Тарифы (переехали в services.pricing)
        
        # Пакеты монет (динамически генерируются из конфигурации)
        "topup.title": "💰 Пополнить монетки",
        
        # Примеры стоимости (переехали в services.pricing)
        
        # Дополнительные действия
        "action.add_prompt": "➕ Добавить промпт",
        "action.edit_replica": "✏️ Редактировать реплику",
        "action.back_final": "⬅️ К финалу",
        "action.generate_replica": "🚀 Генерировать реплику",
        "action.generate_final": "🚀 Генерировать финал",
        "action.manual_replica": "✏️ Ввести реплику вручную",
        "action.cancel_manual": "❌ Отменить ввод",
        "action.var_complex": "🎭 Сложный вариант",
        "action.var_simple": "😊 Простой вариант",
        "action.var_again": "🔄 Другой вариант",
        "action.phrase": "💬 Придумать фразу",
        "action.audio_yes": "🎵 С музыкой",
        "action.audio_no": "🔇 Без музыки",
        "action.cancel_procedure": "❌ Отменить процедуру",
        "action.edit_from_last": "✏️ Редактировать последнее",
        "action.refine_prompt": "✨ Улучшить промпт",
        
        # Сообщения об ошибках
        "error.button_outdated": "Кнопка устарела. Открою меню.",
        "error.low_coins": "💰 Недостаточно монеток",
        "error.skip_low_coins": "⏭️ Продолжить несмотря на низкий баланс",
        
        # Описания функций
        "desc.lego_mode": "Режим для создания LEGO мультиков: генерируем сцены в стиле LEGO с автоматическим стилем!\n\nВыберите тип сюжета:",
        "desc.tryon": "1) Пришлите фото человека, которого будем одевать\n2) Затем пришлите фото одежды (можно даже на другом человеке)",
        "desc.transforms": "💰 У тебя: {coins} монеток\n\n✨ Удалить фон (−1 монетка)\nВырежу фон. Могу поставить белый/градиент/ваш фон.\n\n👥 Совместить людей (−1 монетка)\nСоберу всех в один кадр, как будто снимались вместе.\n\n🧩 Внедрить объект на фото (−1 монетка)\nДобавлю предмет и впишу по свету/перспективе.\n\n🪄 Магическая ретушь (−1 монетка)\nУберу лишнее или добавлю деталь. Можно указать область.\n\n📷 Polaroid (−1 монетка)\nРамка, плёночное зерно, подпись.",
    }
}

def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Получить локализованный текст по ключу"""
    text = T.get(lang, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # Если не удалось форматировать, возвращаем как есть
    return text
