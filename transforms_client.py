# transforms_client.py
# Клиент для обработки изображений: удаление фона, совмещение людей, внедрение объектов, ретушь, Polaroid
# Использует Gemini 2.5 Flash Image для всех трансформаций

import os
import base64
import json
import logging
import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import io
from typing import List, Optional

from google.oauth2 import service_account
from google.auth.transport.requests import Request

log = logging.getLogger("transforms-client")

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GCP_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MODEL_ID = "gemini-2.5-flash-image-preview"

def _load_credentials():
    """Возвращает учётку сервисного аккаунта из ENV."""
    # Сначала пробуем base64 (как в Veo)
    key_b64 = os.getenv("GCP_KEY_JSON_B64")
    if key_b64:
        try:
            key_json = base64.b64decode(key_b64).decode("utf-8")
            creds = service_account.Credentials.from_service_account_info(
                json.loads(key_json), scopes=SCOPES
            )
            return creds
        except Exception as e:
            log.error("Failed to parse GCP_KEY_JSON_B64: %s", e)
    
    # Затем пробуем обычный JSON
    json_str = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if json_str:
        try:
            info = json.loads(json_str)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            return creds
        except Exception as e:
            log.error("Failed to parse GOOGLE_CREDENTIALS_JSON: %s", e)

    # fallback: путь до файла
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if path and os.path.exists(path):
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        return creds

    raise RuntimeError("No Google credentials found. Set GCP_KEY_JSON_B64, GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")

def _access_token() -> str:
    try:
        creds = _load_credentials()
        req = Request()
        creds.refresh(req)
        return creds.token
    except Exception as e:
        log.error("Failed to get access token: %s", e)
        raise RuntimeError(f"Authentication failed: {e}")

def _enhance_image_quality(image_bytes: bytes) -> bytes:
    """Улучшает качество изображения без потери деталей: убирает шум, повышает резкость."""
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Легкое подавление шума
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        # Умеренное повышение резкости
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.15)
        
        # Легкое улучшение контраста
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.05)
        
        # Сохраняем в высоком качестве
        output = io.BytesIO()
        image.save(output, format='PNG', quality=95, optimize=True, compress_level=0)
        return output.getvalue()
        
    except Exception as e:
        log.warning("Failed to enhance image quality: %s", e)
        return image_bytes

def _call_gemini(images: List[bytes], prompt: str, quality: str = "basic") -> bytes:
    """Вызывает Gemini 2.5 Flash Image для обработки изображений."""
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID is not set")

    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:predict"
    )

    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json; charset=utf-8"
    }

    # Подготавливаем изображения
    instances = []
    for img_bytes in images:
        instances.append({
            "image": {"bytesBase64Encoded": base64.b64encode(img_bytes).decode("utf-8")}
        })
    
    # Добавляем промпт
    instances.append({"prompt": prompt})

    # Определяем разрешение
    resolution = "high" if quality == "premium" else "medium"

    payload = {
        "instances": instances,
        "parameters": {
            "sampleCount": 1,
            "resolution": resolution,
            "quality": "high",
            "enhancement": "super_resolution",
            "noise_reduction": True,
            "sharpening": "medium"
        }
    }

    log.info("Transform request → %s", url)
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    if r.status_code >= 400:
        try:
            log.error("Transform error %s: %s", r.status_code, r.text[:1000])
        except Exception:
            pass
        r.raise_for_status()

    data = r.json()
    preds = data.get("predictions") or []
    if not preds:
        raise RuntimeError(f"Empty transform predictions: {data}")

    pred = preds[0]
    if "bytesBase64Encoded" in pred:
        result_bytes = base64.b64decode(pred["bytesBase64Encoded"])
        # Улучшаем качество результата
        enhanced_bytes = _enhance_image_quality(result_bytes)
        return enhanced_bytes

    raise RuntimeError(f"Unexpected transform response structure: {list(pred.keys())}")

def remove_background(image_bytes: bytes, quality: str = "basic") -> bytes:
    """
    Удаляет фон с изображения.
    
    Args:
        image_bytes: байты изображения
        quality: "basic" или "premium"
    
    Returns:
        байты изображения без фона (PNG с прозрачностью)
    """
    prompt = (
        "TASK: Remove background.\n"
        "INSTRUCTIONS:\n"
        "- Isolate the main subject with clean, natural edges (hair detail preserved).\n"
        "- Output with transparent background (alpha), edges anti-aliased.\n"
        "- Keep original subject colors and sharpness; avoid artificial halos.\n"
        "OUTPUT: single PNG with transparency."
    )
    
    return _call_gemini([image_bytes], prompt, quality)

def merge_people(images: List[bytes], quality: str = "basic") -> bytes:
    """
    Совмещает людей из разных фотографий в одну групповую фотографию.
    
    Args:
        images: список байтов изображений (2-3 фото людей)
        quality: "basic" или "premium"
    
    Returns:
        байты группового фото
    """
    prompt = (
        "TASK: Merge people from multiple photos into a single group image.\n"
        "INSTRUCTIONS:\n"
        "- Detect and cut each person with clean edges.\n"
        "- Arrange them close together, natural spacing, eye level aligned.\n"
        "- Match color temperature and shadows so they look shot together.\n"
        "- Use neutral studio background.\n"
        "- Preserve faces, avoid deformation; subtle grain for realism.\n"
        "OUTPUT: single color photo, 3:4 or 1:1 framing."
    )
    
    return _call_gemini(images, prompt, quality)

def inject_object(base_image_bytes: bytes, object_description: str, quality: str = "basic") -> bytes:
    """
    Внедряет объект в изображение по описанию.
    
    Args:
        base_image_bytes: байты базового изображения
        object_description: описание объекта для добавления
        quality: "basic" или "premium"
    
    Returns:
        байты изображения с добавленным объектом
    """
    prompt = (
        f"TASK: Insert an object into the base photo so it looks physically real.\n"
        f"INPUTS:\n"
        f"- text_object: '{object_description}'\n"
        f"INSTRUCTIONS:\n"
        f"- Match perspective, scale, and lighting/shadows to the scene.\n"
        f"- Respect occlusions; add contact shadows.\n"
        f"- Avoid over-saturation; keep object noise/grain consistent with base photo.\n"
        f"OUTPUT: single edited image, same resolution as input."
    )
    
    return _call_gemini([base_image_bytes], prompt, quality)

def retouch_image(image_bytes: bytes, retouch_description: str, quality: str = "basic") -> bytes:
    """
    Выполняет ретушь изображения по описанию.
    
    Args:
        image_bytes: байты изображения
        retouch_description: описание ретуши
        quality: "basic" или "premium"
    
    Returns:
        байты отретушированного изображения
    """
    prompt = (
        f"TASK: Smart retouch (remove or add elements).\n"
        f"INPUTS:\n"
        f"- text_edit: '{retouch_description}'\n"
        f"INSTRUCTIONS:\n"
        f"- If removing: inpaint with background continuation (textures, lines, shadows coherent).\n"
        f"- If adding: match scene lighting, reflections, and color temperature.\n"
        f"- Keep skin texture and fine details; avoid plastic smoothing.\n"
        f"OUTPUT: retouched image, same size as input."
    )
    
    return _call_gemini([image_bytes], prompt, quality)

def create_polaroid(images: List[bytes], quality: str = "basic", caption: str = "") -> bytes:
    """
    Создает Polaroid-стиль изображение из фотографий людей.
    
    Args:
        images: список байтов изображений (1-4 фото людей)
        quality: "basic" или "premium"
        caption: подпись для Polaroid (до 24 символов)
    
    Returns:
        байты изображения в стиле Polaroid
    """
    # Шаг 1 — Сборка кадра (если 2–4 фото)
    if len(images) > 1:
        group_prompt = (
            "TASK: Compose a single group photo from provided portraits.\n"
            "INSTRUCTIONS:\n"
            "- Align faces to similar scale and eye level.\n"
            "- Match color balance, add subtle unified grain.\n"
            "- Neutral background (soft off-white) unless faces are already together.\n"
            "OUTPUT: composed group photo, square or 3:4."
        )
        group_image = _call_gemini(images, group_prompt, quality)
    else:
        group_image = images[0]
    
    # Шаг 2 — Стилизация под Polaroid
    polaroid_prompt = (
        "TASK: Apply Polaroid aesthetic frame and film look.\n"
        "INSTRUCTIONS:\n"
        "- Add classic Polaroid white frame (thicker bottom border).\n"
        "- Apply subtle film grain, soft contrast, slight warm tint.\n"
        "- Make it look like vintage instant camera from 1970s-80s.\n"
        "- Keep image sharp and clear but with nostalgic film aesthetic.\n"
        "OUTPUT: final Polaroid-style image."
    )
    
    if caption:
        polaroid_prompt += f"\n- Place handwritten-style caption at the bottom: '{caption[:24]}'"
    
    return _call_gemini([group_image], polaroid_prompt, quality)

# Функция-роутер для всех трансформаций
def process_transform(transform_type: str, images: List[bytes], text: Optional[str] = None, quality: str = "basic") -> bytes:
    """
    Обрабатывает трансформацию изображения по типу.
    
    Args:
        transform_type: тип трансформации
        images: список байтов изображений
        text: дополнительный текст (для inject_object, retouch)
        quality: "basic" или "premium"
    
    Returns:
        байты обработанного изображения
    """
    if transform_type == "remove_bg":
        return remove_background(images[0], quality)
    elif transform_type == "merge_people":
        return merge_people(images, quality)
    elif transform_type == "inject_object":
        return inject_object(images[0], text or "", quality)
    elif transform_type == "retouch":
        return retouch_image(images[0], text or "", quality)
    elif transform_type == "polaroid":
        return create_polaroid(images, quality)
    else:
        raise ValueError(f"Unknown transform type: {transform_type}")
