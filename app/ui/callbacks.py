# app/ui/callbacks.py
"""Система работы с callback_data для Telegram бота"""

from dataclasses import dataclass
from typing import Optional
import logging

log = logging.getLogger(__name__)

# Разделитель для callback_data (должен быть безопасным для URL)
DELIM = "|"

@dataclass
class Cb:
    """Структура для callback данных"""
    action: str
    id: Optional[str] = None
    extra: Optional[str] = None
    
    def pack(self) -> str:
        """Упаковать callback данные в строку"""
        parts = [self.action]
        if self.id:
            parts.append(self.id)
        if self.extra:
            parts.append(self.extra)
        
        raw = DELIM.join(parts)
        
        # Ограничение Telegram на 64 байта
        if len(raw.encode('utf-8')) > 64:
            log.warning(f"Callback data too long: {raw} ({len(raw.encode('utf-8'))} bytes)")
            # Обрезаем до 64 байт
            while len(raw.encode('utf-8')) > 64 and len(parts) > 1:
                parts.pop()
                raw = DELIM.join(parts)
        
        return raw
    
    @classmethod
    def unpack(cls, data: str) -> Optional['Cb']:
        """Распаковать callback данные из строки"""
        try:
            if not data or not isinstance(data, str):
                return None
            
            parts = data.split(DELIM)
            # Проверяем что есть хотя бы action
            if not parts or not parts[0]:
                return None
            
            # Заполняем недостающие части None
            while len(parts) < 3:
                parts.append(None)
            return cls(parts[0], parts[1], parts[2])
        except Exception as e:
            log.error(f"Failed to parse callback data '{data}': {e}")
            return None
    
    def __str__(self) -> str:
        return f"Cb(action={self.action}, id={self.id}, extra={self.extra})"

def parse_cb(data: str) -> Optional[Cb]:
    """Парсер callback данных с логированием ошибок"""
    if not data:
        return None
    
    cb = Cb.unpack(data)
    if cb:
        log.debug(f"Parsed callback: {cb}")
    else:
        log.warning(f"Failed to parse callback data: '{data}'")
    
    return cb

# Предопределенные действия
class Actions:
    # Навигация
    NAV = "nav"
    HOME = "home"
    BACK = "back"
    CANCEL = "cancel"
    
    # Главное меню
    MENU_MAKE = "make"
    MENU_LEGO = "lego"
    MENU_ALIVE = "alive"
    MENU_TRYON = "tryon"
    MENU_TRANSFORMS = "transforms"
    MENU_JSONPRO = "jsonpro"
    MENU_GUIDES = "guides"
    MENU_PROFILE = "profile"
    MENU_HISTORY = "history"
    
    # Режимы генерации
    MODE_HELPER = "helper"
    MODE_MANUAL = "manual"
    MODE_MEME = "meme"
    MODE_NKUDO = "nkudo"
    
    # LEGO режим
    LEGO_SINGLE = "lego_single"
    LEGO_REPORTAGE = "lego_reportage"
    LEGO_REGENERATE = "lego_regenerate"
    LEGO_IMPROVE = "lego_improve"
    LEGO_KEEP = "lego_keep"
    LEGO_CANCEL = "lego_cancel"
    LEGO_AGAIN = "lego_again"
    LEGO_EMBED_REPLICA = "lego_embed_replica"
    LEGO_MENU_BACK = "lego_menu_back"
    
    # НКУДО режим
    NKUDO_SINGLE = "nkudo_single"
    NKUDO_REPORTAGE = "nkudo_reportage"
    NKUDO_REGENERATE = "nkudo_regenerate"
    NKUDO_IMPROVE = "nkudo_improve"
    NKUDO_KEEP = "nkudo_keep"
    NKUDO_CANCEL = "nkudo_cancel"
    NKUDO_APPROVE = "nkudo_approve"
    NKUDO_REROLL_SCENE1 = "nkudo_reroll_scene1"
    NKUDO_REROLL_SCENE2 = "nkudo_reroll_scene2"
    NKUDO_EDIT_SCENE1 = "nkudo_edit_scene1"
    NKUDO_EDIT_SCENE2 = "nkudo_edit_scene2"
    NKUDO_REGENERATE_REPORT = "nkudo_regenerate_report"
    NKUDO_IMPROVE_REPORT = "nkudo_improve_report"
    NKUDO_EMBED_REPLICA = "nkudo_embed_replica"
    NKUDO_MENU_BACK = "nkudo_menu_back"
    
    # Трансформации
    TRANSFORM_REMOVE_BG = "transform_remove_bg"
    TRANSFORM_MERGE_PEOPLE = "transform_merge_people"
    TRANSFORM_INJECT_OBJECT = "transform_inject_object"
    TRANSFORM_RETOUCH = "transform_retouch"
    TRANSFORM_POLAROID = "transform_polaroid"
    TRANSFORM_QUALITY_BASIC = "quality_basic"
    TRANSFORM_QUALITY_PREMIUM = "quality_premium"
    TRANSFORM_RETRY = "transform_retry"
    
    # Примерочная
    TRYON_START = "tryon_start"
    TRYON_SWAP = "tryon_swap"
    TRYON_RESET = "tryon_reset"
    TRYON_CONFIRM = "tryon_confirm"
    TRYON_NEW_POSE = "tryon_new_pose"
    TRYON_NEW_GARMENT = "tryon_new_garment"
    TRYON_NEW_BG = "tryon_new_bg"
    TRYON_PROMPT = "tryon_prompt"
    
    # Стили
    STYLE_ANIME = "style_anime"
    STYLE_LEGO = "style_lego"
    STYLE_NONE = "style_none"
    
    # Ориентация
    ORIENTATION_PORTRAIT = "ori_916"
    ORIENTATION_LANDSCAPE = "ori_169"
    
    # JSON Pro
    JSONPRO_ENTER = "jsonpro_enter"
    JSONPRO_ORI_916 = "jsonpro_ori_916"
    JSONPRO_ORI_169 = "jsonpro_ori_169"
    JSONPRO_GENERATE = "jsonpro_generate"
    
    # Платежи и тарифы
    PAYMENT_PLANS = "show_plans"
    PAYMENT_TOPUP = "show_topup"
    PAYMENT_TERMS = "show_terms"
    PAYMENT_SUPPORT = "contact_support"
    PAYMENT_CHANGE_PLAN = "change_plan"
    PAYMENT_SHOW_HISTORY = "show_history"
    
    # Дополнительные действия
    ACTION_ADD_PROMPT = "prompt_add"
    ACTION_EDIT_REPLICA = "edit_replica_final"
    ACTION_BACK_FINAL = "back_to_final"
    ACTION_GENERATE_REPLICA = "generate_replica"
    ACTION_GENERATE_FINAL = "generate_replica_final"
    ACTION_MANUAL_REPLICA = "manual_replica"
    ACTION_CANCEL_MANUAL = "cancel_manual_replica"
    ACTION_VAR_COMPLEX = "var_complex"
    ACTION_VAR_SIMPLE = "var_simple"
    ACTION_VAR_AGAIN = "var_again"
    ACTION_PHRASE = "phrase"
    ACTION_AUDIO_YES = "audio_yes"
    ACTION_AUDIO_NO = "audio_no"
    ACTION_CANCEL_PROCEDURE = "cancel_procedure"
    ACTION_EDIT_FROM_LAST = "edit_from_last"
    ACTION_REFINE_PROMPT = "refine_prompt"
    
    # Специальные действия
    SCENE_SAVE = "scene_save"
    SCENE_CANCEL = "scene_cancel"
    SKIP_LOW_COINS = "skip_low_coins"
    VIDEO_RETRY = "video_retry"
    MEME_AGAIN = "meme_again"
    MEME_TO_HELPER = "meme_to_helper"
    BACK_MODES = "back_modes"
    IMPROVE_KEEP = "improve_keep"
    IMPROVE_CANCEL = "improve_cancel"
    REPORT_IMPROVE_KEEP = "report_improve_keep"
    REPORT_IMPROVE_CANCEL = "report_improve_cancel"
    GENERATE_NOW = "generate_now"
    GO_ORIENTATION = "go_orientation"
