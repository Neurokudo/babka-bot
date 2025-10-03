# tryon_client.py
# Клиент для Vertex AI Virtual Try-On (virtual-try-on-preview-08-04)

import os
import base64
import json
import logging
import time
import requests
from PIL import Image, ImageEnhance, ImageFilter
import io

from google.oauth2 import service_account
from google.auth.transport.requests import Request

log = logging.getLogger("tryon-client")

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "ornate-producer-473220-g2")
LOCATION = os.getenv("GCP_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MODEL_ID = "virtual-try-on-preview-08-04"
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
TRYON_HTTP_TIMEOUT = int(os.getenv("TRYON_HTTP_TIMEOUT", "240"))

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
        # Если JWT подпись неверная, попробуем перезагрузить credentials
        if "Invalid JWT Signature" in str(e) or "invalid_grant" in str(e):
            log.warning("JWT signature invalid, attempting to reload credentials...")
            # Очищаем кеш и пробуем снова
            try:
                creds = _load_credentials()
                req = Request()
                creds.refresh(req)
                return creds.token
            except Exception as e2:
                log.error("Failed to reload credentials: %s", e2)
                raise RuntimeError(f"Authentication failed: {e2}")
        else:
            raise RuntimeError(f"Authentication failed: {e}")


def _post_with_retry(url: str, headers: dict, payload: dict,
                     timeout: int = TRYON_HTTP_TIMEOUT,
                     attempts: int = HTTP_RETRIES):
    backoff = 2
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code < 400:
                return response

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = RuntimeError(
                    f"Retryable error {response.status_code}: {response.text[:512]}"
                )
            else:
                response.raise_for_status()
        except requests.RequestException as exc:
            last_error = exc

        if attempt < attempts:
            sleep_for = backoff ** (attempt - 1)
            log.warning("Try-on request retry %s/%s after %s", attempt, attempts, last_error)
            time.sleep(min(20, sleep_for))

    raise RuntimeError(f"Try-on request failed after {attempts} attempts: {last_error}")

def _enhance_image_quality(image_bytes: bytes) -> bytes:
    """Улучшает качество изображения без потери деталей: убирает шум, повышает резкость."""
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Сохраняем оригинальный размер
        original_size = image.size
        
        # Легкое подавление шума (более мягкий подход)
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        # Умеренное повышение резкости (не слишком агрессивно)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)  # Было 1.8, теперь 1.2
        
        # Легкое улучшение контраста
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)  # Было 1.3, теперь 1.1
        
        # Сохраняем в высоком качестве без потери деталей
        output = io.BytesIO()
        image.save(output, format='PNG', quality=95, optimize=True, compress_level=0)
        return output.getvalue()
        
    except Exception as e:
        log.warning("Failed to enhance image quality: %s", e)
        return image_bytes  # Возвращаем оригинал если не удалось улучшить

def virtual_tryon(person_bytes: bytes, garment_bytes: bytes, sample_count: int = 1):
    """
    Вызывает Vertex AI VTO. Возвращает PNG-байты результата или словарь с gcsUri.
    """
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

    payload = {
        "instances": [{
            "personImage": {"image": {"bytesBase64Encoded": base64.b64encode(person_bytes).decode("utf-8")}},
            "productImages": [
                {"image": {"bytesBase64Encoded": base64.b64encode(garment_bytes).decode("utf-8")}}
            ]
        }],
        "parameters": {
            "sampleCount": int(sample_count),
            "quality": "ultra_high",  # Максимальное качество
            "resolution": "high",  # Высокое разрешение
            "enhancement": "super_resolution",  # Супер-разрешение
            "noise_reduction": True,  # Подавление шума
            "sharpening": "medium",  # Умеренная резкость (не слишком агрессивно)
            "color_correction": True,  # Коррекция цвета
            "detail_preservation": True  # Сохранение деталей
            # "storageUri": "gs://your-bucket/path/"  # если хочешь сохранять в GCS
        }
    }

    log.info("VTO request → %s", url)
    r = _post_with_retry(url, headers, payload)

    data = r.json()
    preds = data.get("predictions") or []
    if not preds:
        raise RuntimeError(f"Empty VTO predictions: {data}")

    pred = preds[0]
    if "bytesBase64Encoded" in pred:
        result_bytes = base64.b64decode(pred["bytesBase64Encoded"])
        # Улучшаем качество результата
        enhanced_bytes = _enhance_image_quality(result_bytes)
        return enhanced_bytes
    if "gcsUri" in pred:
        return {"gcsUri": pred["gcsUri"]}

    raise RuntimeError(f"Unexpected VTO response structure: {list(pred.keys())}")
