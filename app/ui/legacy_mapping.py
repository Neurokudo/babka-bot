# app/ui/legacy_mapping.py
"""Маппинг старых callback-ов для обратной совместимости"""

from app.ui.callbacks import Actions, Cb

# Маппинг старых callback-ов на новые действия
OLD_CALLBACK_MAP = {
    # Главное меню
    "menu_make": Actions.MENU_MAKE,
    "menu_lego": Actions.MENU_LEGO,
    "menu_alive": Actions.MENU_ALIVE,
    "menu_tryon": Actions.MENU_TRYON,
    "menu_transforms": Actions.MENU_TRANSFORMS,
    "menu_jsonpro": Actions.MENU_JSONPRO,
    "menu_guides": Actions.MENU_GUIDES,
    "menu_profile": Actions.MENU_PROFILE,
    "show_history": Actions.MENU_HISTORY,
    
    # Навигация
    "back_home": (Actions.NAV, "root"),
    "back_modes": (Actions.NAV, "modes"),
    
    # Режимы генерации
    "mode_helper": Actions.MODE_HELPER,
    "mode_manual": Actions.MODE_MANUAL,
    "mode_meme": Actions.MODE_MEME,
    "mode_nkudo": Actions.MODE_NKUDO,
    
    # LEGO режим
    "lego_single": Actions.LEGO_SINGLE,
    "lego_reportage": Actions.LEGO_REPORTAGE,
    "lego_regenerate_single": Actions.LEGO_REGENERATE,
    "lego_improve_single": Actions.LEGO_IMPROVE,
    "lego_improve_keep": Actions.LEGO_KEEP,
    "lego_improve_cancel": Actions.LEGO_CANCEL,
    "lego_improve_again": Actions.LEGO_AGAIN,
    "lego_embed_replica": Actions.LEGO_EMBED_REPLICA,
    "lego_menu_back": Actions.LEGO_MENU_BACK,
    
    # НКУДО режим
    "nkudo_single": Actions.NKUDO_SINGLE,
    "nkudo_reportage": Actions.NKUDO_REPORTAGE,
    "nkudo_regenerate_single": Actions.NKUDO_REGENERATE,
    "nkudo_improve_single": Actions.NKUDO_IMPROVE,
    "improve_keep": Actions.NKUDO_KEEP,
    "improve_cancel": Actions.NKUDO_CANCEL,
    "nkudo_embed_replica": Actions.NKUDO_EMBED_REPLICA,
    "nkudo_menu_back": Actions.NKUDO_MENU_BACK,
    "nkudo_reroll_scene1": Actions.NKUDO_REROLL_SCENE1,
    "nkudo_reroll_scene2": Actions.NKUDO_REROLL_SCENE2,
    "nkudo_edit_scene1": Actions.NKUDO_EDIT_SCENE1,
    "nkudo_edit_scene2": Actions.NKUDO_EDIT_SCENE2,
    "nkudo_regenerate_report": Actions.NKUDO_REGENERATE_REPORT,
    "nkudo_improve_report": Actions.NKUDO_IMPROVE_REPORT,
    "nkudo_approve": Actions.NKUDO_APPROVE,
    
    # Трансформации
    "transform_remove_bg": Actions.TRANSFORM_REMOVE_BG,
    "transform_merge_people": Actions.TRANSFORM_MERGE_PEOPLE,
    "transform_inject_object": Actions.TRANSFORM_INJECT_OBJECT,
    "transform_retouch": Actions.TRANSFORM_RETOUCH,
    "transform_polaroid": Actions.TRANSFORM_POLAROID,
    "quality_basic": Actions.TRANSFORM_QUALITY_BASIC,
    "quality_premium": Actions.TRANSFORM_QUALITY_PREMIUM,
    "transform_retry": Actions.TRANSFORM_RETRY,
    
    # Примерочная
    "tryon_swap": Actions.TRYON_SWAP,
    "tryon_reset": Actions.TRYON_RESET,
    "tryon_confirm": Actions.TRYON_CONFIRM,
    "tryon_new_pose": Actions.TRYON_NEW_POSE,
    "tryon_new_garment": Actions.TRYON_NEW_GARMENT,
    "tryon_new_bg": Actions.TRYON_NEW_BG,
    "tryon_prompt": Actions.TRYON_PROMPT,
    
    # Стили
    "style_Анимэ": Actions.STYLE_ANIME,
    "style_LEGO": Actions.STYLE_LEGO,
    "style_None": Actions.STYLE_NONE,
    
    # Ориентация
    "ori_916": Actions.ORIENTATION_PORTRAIT,
    "ori_169": Actions.ORIENTATION_LANDSCAPE,
    
    # JSON Pro
    "jsonpro_enter": Actions.JSONPRO_ENTER,
    "jsonpro_ori_916": Actions.JSONPRO_ORI_916,
    "jsonpro_ori_169": Actions.JSONPRO_ORI_169,
    "jsonpro_generate": Actions.JSONPRO_GENERATE,
    
    # Платежи
    "show_plans": Actions.PAYMENT_PLANS,
    "show_tariffs": Actions.PAYMENT_PLANS,  # Добавлено для обратной совместимости
    "show_topup": Actions.PAYMENT_TOPUP,
    "show_terms": Actions.PAYMENT_TERMS,
    "contact_support": Actions.PAYMENT_SUPPORT,
    "change_plan": Actions.PAYMENT_CHANGE_PLAN,
    "show_addons": Actions.PAYMENT_SHOW_HISTORY,
    
    # Специальные действия
    "scene_save": Actions.SCENE_SAVE,
    "scene_cancel": Actions.SCENE_CANCEL,
    "skip_low_coins": Actions.SKIP_LOW_COINS,
    "video_retry": Actions.VIDEO_RETRY,
    "meme_again": Actions.MEME_AGAIN,
    "meme_to_helper": Actions.MEME_TO_HELPER,
    
    # Дополнительные действия
    "prompt_add": Actions.ACTION_ADD_PROMPT,
    "edit_replica_final": Actions.ACTION_EDIT_REPLICA,
    "back_to_final": Actions.ACTION_BACK_FINAL,
    "generate_replica": Actions.ACTION_GENERATE_REPLICA,
    "generate_replica_final": Actions.ACTION_GENERATE_FINAL,
    "manual_replica": Actions.ACTION_MANUAL_REPLICA,
    "cancel_manual_replica": Actions.ACTION_CANCEL_MANUAL,
    "var_complex": Actions.ACTION_VAR_COMPLEX,
    "var_simple": Actions.ACTION_VAR_SIMPLE,
    "var_again": Actions.ACTION_VAR_AGAIN,
    "phrase": Actions.ACTION_PHRASE,
    "audio_yes": Actions.ACTION_AUDIO_YES,
    "audio_no": Actions.ACTION_AUDIO_NO,
    "cancel_procedure": Actions.ACTION_CANCEL_PROCEDURE,
    "edit_from_last": Actions.ACTION_EDIT_FROM_LAST,
    "refine_prompt": Actions.ACTION_REFINE_PROMPT,
    "generate_now": Actions.GENERATE_NOW,
    "go_orientation": Actions.GO_ORIENTATION,
    
    # Улучшения
    "report_improve_keep": Actions.REPORT_IMPROVE_KEEP,
    "report_improve_cancel": Actions.REPORT_IMPROVE_CANCEL,
}

def convert_legacy_callback(callback_data: str) -> Cb:
    """Конвертировать старый callback в новый формат"""
    if not callback_data:
        return None
    
    if callback_data in OLD_CALLBACK_MAP:
        mapping = OLD_CALLBACK_MAP[callback_data]
        if isinstance(mapping, tuple):
            # Действие с параметрами (action, id, extra)
            result = Cb(*mapping)
            print(f"🔍 LEGACY CONVERSION: '{callback_data}' -> {result}")
            return result
        else:
            # Простое действие
            result = Cb(mapping)
            print(f"🔍 LEGACY CONVERSION: '{callback_data}' -> {result}")
            return result
    
    print(f"❌ LEGACY CONVERSION FAILED: '{callback_data}' not found in mapping")
    return None

def is_legacy_callback(callback_data: str) -> bool:
    """Проверить является ли callback старым форматом"""
    return callback_data in OLD_CALLBACK_MAP

def get_legacy_callback_count() -> int:
    """Получить количество поддерживаемых старых callback-ов"""
    return len(OLD_CALLBACK_MAP)

def list_legacy_callbacks() -> list:
    """Получить список всех поддерживаемых старых callback-ов"""
    return list(OLD_CALLBACK_MAP.keys())
