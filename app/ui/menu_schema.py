# app/ui/menu_schema.py
"""Декларативная схема меню и переходов бота"""

from app.ui.callbacks import Actions

MENU = {
    "root": {
        "text_key": "menu.title",
        "buttons": [
            {"text_key": "btn.generate", "to": "modes", "cb": (Actions.MODE_HELPER,)},
            {"text_key": "btn.lego", "to": "lego_menu", "cb": (Actions.LEGO_SINGLE,)},
            {"text_key": "btn.alive", "to": "modes", "cb": (Actions.MODE_HELPER,)},
            {"text_key": "btn.tryon", "to": "tryon_start", "cb": (Actions.TRYON_START,)},
            {"text_key": "btn.transforms", "to": "transforms", "cb": (Actions.TRANSFORM_REMOVE_BG,)},
            {"text_key": "btn.jsonpro", "to": "jsonpro_start", "cb": (Actions.JSONPRO_ENTER,)},
            {"text_key": "btn.guides", "to": "guides", "cb": (Actions.MENU_GUIDES,)},
            {"text_key": "btn.profile", "to": "profile", "cb": (Actions.MENU_PROFILE,)},
        ],
    },

    "guides": {
        "text_key": "menu.guides",
        "buttons": [
            {"text_key": "payment.plans", "to": "guides", "cb": (Actions.PAYMENT_PLANS,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "modes": {
        "text_key": "menu.generate",
        "buttons": [
            {"text_key": "mode.helper", "to": "modes", "cb": (Actions.MODE_HELPER,)},
            {"text_key": "mode.manual", "to": "modes", "cb": (Actions.MODE_MANUAL,)},
            {"text_key": "mode.meme", "to": "modes", "cb": (Actions.MODE_MEME,)},
            {"text_key": "mode.nkudo", "to": "nkudo_menu", "cb": (Actions.MODE_NKUDO,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.BACK_MODES,)},
        ],
    },
    
    "lego_menu": {
        "text_key": "menu.lego",
        "description_key": "desc.lego_mode",
        "buttons": [
            {"text_key": "lego.single", "to": "lego_single", "cb": (Actions.LEGO_SINGLE,)},
            {"text_key": "lego.reportage", "to": "lego_reportage", "cb": (Actions.LEGO_REPORTAGE,)},
            {"text_key": "lego.menu_back", "to": "root", "cb": (Actions.LEGO_MENU_BACK,)},
        ],
    },
    
    "lego_single": {
        "text_key": "lego.single",
        "buttons": [
            {"text_key": "lego.regenerate", "to": "lego_single", "cb": (Actions.LEGO_REGENERATE,)},
            {"text_key": "lego.improve", "to": "lego_single", "cb": (Actions.LEGO_IMPROVE,)},
            {"text_key": "lego.embed_replica", "to": "lego_single", "cb": (Actions.LEGO_EMBED_REPLICA,)},
            {"text_key": "btn.back", "to": "lego_menu", "cb": (Actions.NAV, "lego_menu")},
        ],
    },
    
    "lego_reportage": {
        "text_key": "lego.reportage",
        "buttons": [
            {"text_key": "btn.back", "to": "lego_menu", "cb": (Actions.NAV, "lego_menu")},
        ],
    },
    
    "nkudo_menu": {
        "text_key": "mode.nkudo",
        "buttons": [
            {"text_key": "nkudo.single", "to": "nkudo_single", "cb": (Actions.NKUDO_SINGLE,)},
            {"text_key": "nkudo.reportage", "to": "nkudo_reportage", "cb": (Actions.NKUDO_REPORTAGE,)},
            {"text_key": "nkudo.menu_back", "to": "modes", "cb": (Actions.NKUDO_MENU_BACK,)},
        ],
    },
    
    "nkudo_single": {
        "text_key": "nkudo.single",
        "buttons": [
            {"text_key": "nkudo.regenerate", "to": "nkudo_single", "cb": (Actions.NKUDO_REGENERATE,)},
            {"text_key": "nkudo.improve", "to": "nkudo_single", "cb": (Actions.NKUDO_IMPROVE,)},
            {"text_key": "nkudo.embed_replica", "to": "nkudo_single", "cb": (Actions.NKUDO_EMBED_REPLICA,)},
            {"text_key": "btn.back", "to": "nkudo_menu", "cb": (Actions.NAV, "nkudo_menu")},
        ],
    },
    
    "nkudo_reportage": {
        "text_key": "nkudo.reportage",
        "buttons": [
            {"text_key": "nkudo.reroll_scene1", "to": "nkudo_reportage", "cb": (Actions.NKUDO_REROLL_SCENE1,)},
            {"text_key": "nkudo.reroll_scene2", "to": "nkudo_reportage", "cb": (Actions.NKUDO_REROLL_SCENE2,)},
            {"text_key": "nkudo.edit_scene1", "to": "nkudo_reportage", "cb": (Actions.NKUDO_EDIT_SCENE1,)},
            {"text_key": "nkudo.edit_scene2", "to": "nkudo_reportage", "cb": (Actions.NKUDO_EDIT_SCENE2,)},
            {"text_key": "nkudo.regenerate_report", "to": "nkudo_reportage", "cb": (Actions.NKUDO_REGENERATE_REPORT,)},
            {"text_key": "nkudo.improve_report", "to": "nkudo_reportage", "cb": (Actions.NKUDO_IMPROVE_REPORT,)},
            {"text_key": "nkudo.approve", "to": "nkudo_reportage", "cb": (Actions.NKUDO_APPROVE,)},
            {"text_key": "btn.back", "to": "nkudo_menu", "cb": (Actions.NAV, "nkudo_menu")},
        ],
    },
    
    "tryon_start": {
        "text_key": "menu.tryon",
        "description_key": "desc.tryon",
        "buttons": [
            {"text_key": "tryon.start", "to": "tryon_start", "cb": (Actions.TRYON_START,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "tryon_confirm": {
        "text_key": "tryon.confirm",
        "buttons": [
            {"text_key": "tryon.confirm", "to": "tryon_confirm", "cb": (Actions.TRYON_CONFIRM,)},
            {"text_key": "btn.back", "to": "tryon_start", "cb": (Actions.NAV, "tryon_start")},
        ],
    },
    
    "tryon_after": {
        "text_key": "tryon.after",
        "buttons": [
            {"text_key": "tryon.swap", "to": "tryon_after", "cb": (Actions.TRYON_SWAP,)},
            {"text_key": "tryon.reset", "to": "tryon_after", "cb": (Actions.TRYON_RESET,)},
            {"text_key": "tryon.new_pose", "to": "tryon_after", "cb": (Actions.TRYON_NEW_POSE,)},
            {"text_key": "tryon.new_garment", "to": "tryon_after", "cb": (Actions.TRYON_NEW_GARMENT,)},
            {"text_key": "tryon.new_bg", "to": "tryon_after", "cb": (Actions.TRYON_NEW_BG,)},
            {"text_key": "tryon.prompt", "to": "tryon_after", "cb": (Actions.TRYON_PROMPT,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "transforms": {
        "text_key": "menu.transforms",
        "description_key": "desc.transforms",
        "buttons": [
            {"text_key": "transform.remove_bg", "to": "transforms", "cb": (Actions.TRANSFORM_REMOVE_BG,)},
            {"text_key": "transform.merge_people", "to": "transforms", "cb": (Actions.TRANSFORM_MERGE_PEOPLE,)},
            {"text_key": "transform.inject_object", "to": "transforms", "cb": (Actions.TRANSFORM_INJECT_OBJECT,)},
            {"text_key": "transform.retouch", "to": "transforms", "cb": (Actions.TRANSFORM_RETOUCH,)},
            {"text_key": "transform.polaroid", "to": "transforms", "cb": (Actions.TRANSFORM_POLAROID,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "transform_quality": {
        "text_key": "transform.quality",
        "buttons": [
            {"text_key": "transform.quality_basic", "to": "transform_quality", "cb": (Actions.TRANSFORM_QUALITY_BASIC,)},
            {"text_key": "transform.quality_premium", "to": "transform_quality", "cb": (Actions.TRANSFORM_QUALITY_PREMIUM,)},
            {"text_key": "btn.back", "to": "transforms", "cb": (Actions.NAV, "transforms")},
        ],
    },
    
    "jsonpro_start": {
        "text_key": "menu.jsonpro",
        "buttons": [
            {"text_key": "jsonpro.enter", "to": "jsonpro_start", "cb": (Actions.JSONPRO_ENTER,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "jsonpro_orientation": {
        "text_key": "jsonpro.orientation",
        "buttons": [
            {"text_key": "jsonpro.ori_916", "to": "jsonpro_orientation", "cb": (Actions.JSONPRO_ORI_916,)},
            {"text_key": "jsonpro.ori_169", "to": "jsonpro_orientation", "cb": (Actions.JSONPRO_ORI_169,)},
            {"text_key": "jsonpro.generate", "to": "jsonpro_orientation", "cb": (Actions.JSONPRO_GENERATE,)},
            {"text_key": "btn.back", "to": "jsonpro_start", "cb": (Actions.NAV, "jsonpro_start")},
        ],
    },
    
    "profile": {
        "text_key": "menu.profile",
        "buttons": [
            {"text_key": "payment.plans", "to": "profile", "cb": (Actions.PAYMENT_PLANS,)},
            {"text_key": "payment.topup", "to": "profile", "cb": (Actions.PAYMENT_TOPUP,)},
            {"text_key": "payment.change_plan", "to": "profile", "cb": (Actions.PAYMENT_CHANGE_PLAN,)},
            {"text_key": "payment.show_history", "to": "profile", "cb": (Actions.PAYMENT_SHOW_HISTORY,)},
            {"text_key": "payment.terms", "to": "profile", "cb": (Actions.PAYMENT_TERMS,)},
            {"text_key": "payment.support", "to": "profile", "cb": (Actions.PAYMENT_SUPPORT,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "styles": {
        "text_key": "style.choose",
        "buttons": [
            {"text_key": "style.anime", "to": "styles", "cb": (Actions.STYLE_ANIME,)},
            {"text_key": "style.lego", "to": "styles", "cb": (Actions.STYLE_LEGO,)},
            {"text_key": "style.none", "to": "styles", "cb": (Actions.STYLE_NONE,)},
        ],
    },
    
    "orientation": {
        "text_key": "orientation.choose",
        "buttons": [
            {"text_key": "orientation.portrait", "to": "orientation", "cb": (Actions.ORIENTATION_PORTRAIT,)},
            {"text_key": "orientation.landscape", "to": "orientation", "cb": (Actions.ORIENTATION_LANDSCAPE,)},
        ],
    },
    
    "scene_edit": {
        "text_key": "scene.edit",
        "buttons": [
            {"text_key": "btn.save", "to": "scene_edit", "cb": (Actions.SCENE_SAVE,)},
            {"text_key": "btn.cancel", "to": "scene_edit", "cb": (Actions.SCENE_CANCEL,)},
        ],
    },
    
    "meme": {
        "text_key": "mode.meme",
        "buttons": [
            {"text_key": "meme.again", "to": "meme", "cb": (Actions.MEME_AGAIN,)},
            {"text_key": "meme.to_helper", "to": "meme", "cb": (Actions.MEME_TO_HELPER,)},
            {"text_key": "btn.back", "to": "modes", "cb": (Actions.NAV, "modes")},
        ],
    },
    
    "video_result": {
        "text_key": "video.result",
        "buttons": [
            {"text_key": "btn.retry", "to": "video_result", "cb": (Actions.VIDEO_RETRY,)},
            {"text_key": "btn.back", "to": "root", "cb": (Actions.NAV, "root")},
        ],
    },
    
    "transform_result": {
        "text_key": "transform.result",
        "buttons": [
            {"text_key": "btn.retry", "to": "transform_result", "cb": (Actions.TRANSFORM_RETRY,)},
            {"text_key": "btn.back", "to": "transforms", "cb": (Actions.NAV, "transforms")},
        ],
    },
    
    "low_coins_warning": {
        "text_key": "error.low_coins",
        "buttons": [
            {"text_key": "error.skip_low_coins", "to": "low_coins_warning", "cb": (Actions.SKIP_LOW_COINS,)},
            {"text_key": "payment.topup", "to": "low_coins_warning", "cb": (Actions.PAYMENT_TOPUP,)},
        ],
    },
}

def get_menu_node(node_id: str):
    """Получить узел меню по ID"""
    return MENU.get(node_id)

def get_all_node_ids():
    """Получить все ID узлов меню"""
    return set(MENU.keys())

def validate_menu_schema():
    """Валидация схемы меню"""
    errors = []
    
    # Проверяем, что все 'to' ссылки существуют
    for node_id, node in MENU.items():
        for button in node.get("buttons", []):
            target = button.get("to")
            if target and target not in MENU:
                errors.append(f"Node '{node_id}' references non-existent target '{target}'")
    
    return errors
