#!/usr/bin/env python3
"""
bg_removal.py - Специальный модуль для удаления фона с изображений
Использует Gemini 2.5 Flash для качественного удаления фона и создания файлов PNG и JPG
"""

import os
import base64
import json
import logging
import requests
import io
from PIL import Image
from typing import Tuple, Optional

from google.oauth2 import service_account
from google.auth.transport.requests import Request

log = logging.getLogger("bg-removal")

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

def _call_gemini_for_bg_removal(image_bytes: bytes, quality: str = "basic") -> bytes:
    """Вызывает Gemini 2.5 Flash для удаления фона."""
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

    # Улучшенный промпт для удаления фона
    prompt = (
        "ЗАДАЧА: Профессиональное удаление фона с изображения.\n\n"
        "ТРЕБОВАНИЯ:\n"
        "- Точно выделить главный объект/человека, сохранив ВСЕ детали (волосы, мех, тонкие элементы)\n"
        "- Создать идеально прозрачный фон (альфа-канал = 0)\n"
        "- Применить качественное сглаживание краев (anti-aliasing)\n"
        "- Сохранить естественные края без искусственных ореолов\n"
        "- Сохранить оригинальные цвета, контрастность и резкость объекта\n"
        "- Полностью убрать фон, включая тени и отражения\n"
        "- Обработать сложные области (волосы, прозрачные объекты) с максимальной точностью\n\n"
        "РЕЗУЛЬТАТ: PNG файл с полной прозрачностью фона и профессиональным качеством краев."
    )

    # Определяем разрешение
    resolution = "2048x2048" if quality == "premium" else "1024x1024"

    payload = {
        "instances": [
            {
                "image": {"bytesBase64Encoded": base64.b64encode(image_bytes).decode("utf-8")}
            },
            {
                "prompt": prompt
            }
        ],
        "parameters": {
            "sampleCount": 1,
            "resolution": resolution,
            "quality": "high",
            "enhancement": "super_resolution",
            "noise_reduction": True,
            "sharpening": "medium",
            "background_removal": True  # Специальный параметр для удаления фона
        }
    }

    log.info("Background removal request → %s", url)
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    if r.status_code >= 400:
        try:
            log.error("Background removal error %s: %s", r.status_code, r.text[:1000])
        except Exception:
            pass
        r.raise_for_status()

    data = r.json()
    preds = data.get("predictions") or []
    if not preds:
        raise RuntimeError(f"Empty background removal predictions: {data}")

    pred = preds[0]
    if "bytesBase64Encoded" in pred:
        result_bytes = base64.b64decode(pred["bytesBase64Encoded"])
        return result_bytes

    raise RuntimeError(f"Unexpected background removal response structure: {list(pred.keys())}")

def create_green_background_jpg(png_bytes: bytes) -> bytes:
    """Создает JPG файл с зеленым фоном из PNG с прозрачностью."""
    try:
        # Открываем PNG с прозрачностью
        png_image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        
        # Создаем зеленый фон (chroma key green - стандартный цвет для хромакея)
        chroma_green = (0, 177, 64)  # Стандартный chroma key зеленый
        green_bg = Image.new("RGB", png_image.size, chroma_green)
        
        # Накладываем объект на зеленый фон с учетом альфа-канала
        green_bg.paste(png_image, (0, 0), png_image)
        
        # Сохраняем как JPG с высоким качеством
        jpg_buffer = io.BytesIO()
        green_bg.save(jpg_buffer, format="JPEG", quality=98, optimize=True)
        return jpg_buffer.getvalue()
        
    except Exception as e:
        log.error("Failed to create green background JPG: %s", e)
        raise RuntimeError(f"Ошибка создания JPG с зеленым фоном: {str(e)}")

def process_background_removal(image_bytes: bytes, quality: str = "basic") -> Tuple[bytes, bytes]:
    """
    Обрабатывает удаление фона и создает два файла: PNG с прозрачностью и JPG с зеленым фоном.
    
    Args:
        image_bytes: байты исходного изображения
        quality: "basic" или "premium"
    
    Returns:
        Tuple[bytes, bytes]: (PNG с прозрачным фоном, JPG с зеленым фоном)
    
    Raises:
        RuntimeError: при ошибках обработки
        ValueError: при некорректных входных данных
    """
    if not image_bytes:
        raise ValueError("Не предоставлено изображение для удаления фона")
    
    try:
        log.info("Starting background removal process, quality: %s", quality)
        
        # Шаг 1: Удаляем фон через Gemini
        png_bytes = _call_gemini_for_bg_removal(image_bytes, quality)
        log.info("Background removed successfully, PNG size: %d bytes", len(png_bytes))
        
        # Шаг 2: Создаем JPG с зеленым фоном
        jpg_bytes = create_green_background_jpg(png_bytes)
        log.info("Green background JPG created successfully, size: %d bytes", len(jpg_bytes))
        
        return png_bytes, jpg_bytes
        
    except Exception as e:
        log.error("Background removal process failed: %s", e)
        raise RuntimeError(f"Ошибка удаления фона: {str(e)}")

def validate_image(image_bytes: bytes) -> bool:
    """Проверяет, что переданные байты являются корректным изображением."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Проверяем, что изображение можно открыть и получить размеры
        width, height = image.size
        if width < 10 or height < 10:
            return False
        if width > 4096 or height > 4096:
            log.warning("Image is very large: %dx%d", width, height)
        return True
    except Exception as e:
        log.error("Image validation failed: %s", e)
        return False

# Основная функция для использования в main.py
def remove_background_complete(image_bytes: bytes, quality: str = "basic") -> Tuple[bytes, bytes]:
    """
    Полная обработка удаления фона с валидацией.
    
    Args:
        image_bytes: байты изображения
        quality: "basic" или "premium"
    
    Returns:
        Tuple[bytes, bytes]: (PNG с прозрачным фоном, JPG с зеленым фоном)
    """
    # Валидация входных данных
    if not validate_image(image_bytes):
        raise ValueError("Некорректное изображение или неподдерживаемый формат")
    
    # Обработка
    return process_background_removal(image_bytes, quality)
