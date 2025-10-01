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
    resolution = "2048x2048" if quality == "premium" else "1024x1024"

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
        "Remove the background from this image completely. "
        "Keep only the main subject with clean, precise edges. "
        "Output should have transparent background (PNG format). "
        "Preserve all details of the subject including hair, clothing, and accessories."
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
        "Create a realistic group photo by merging the people from these separate images. "
        "Place them close together with natural spacing and eye level alignment. "
        "Unify lighting, color temperature, and exposure so they look like they were photographed together. "
        "Use a soft, neutral background. "
        "Preserve each person's identity and facial features. "
        "Make it look completely natural and realistic."
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
        f"Add the following object to this image: '{object_description}'. "
        "Make it look completely natural and realistic. "
        "Match the lighting, shadows, perspective, and scale of the scene. "
        "Ensure proper occlusion (objects in front/behind each other). "
        "Add contact shadows and reflections if appropriate. "
        "Maintain the original image's quality and style."
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
        f"Perform the following retouching on this image: '{retouch_description}'. "
        "Make the changes look completely natural and realistic. "
        "If removing objects, fill the space with coherent background elements. "
        "If adding elements, match the scene's lighting, color, and style. "
        "Preserve skin texture and fine details. "
        "Do not alter the person's identity or pose significantly."
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
    # Сначала создаем групповое фото
    if len(images) > 1:
        group_prompt = (
            "Create a clean group portrait by merging the people from these separate images. "
            "Place them close together with natural spacing and eye level alignment. "
            "Use soft, even lighting and neutral background. "
            "Preserve each person's identity and facial features."
        )
        group_image = _call_gemini(images, group_prompt, quality)
    else:
        group_image = images[0]
    
    # Затем применяем Polaroid стиль
    polaroid_prompt = (
        "Transform this image into a vintage Polaroid photograph style. "
        "Add the characteristic white border with rounded corners. "
        "Apply vintage film grain and slightly warm color tone. "
        "Make the image look like it was taken with an instant camera from the 1970s-80s. "
        "Keep the image sharp and clear but with nostalgic film aesthetic."
    )
    
    if caption:
        polaroid_prompt += f" Add handwritten-style caption at the bottom: '{caption[:24]}'"
    
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
