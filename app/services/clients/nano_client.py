# nano_client.py
# Экспериментальная «перепостановка» уже одетой модели:
# - изменить позу/ракурс по описанию
# - заменить фон (новая локация)
# Использует Gemini 2.5 Flash Image (preview).

import os, base64, json, logging, time, requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from PIL import Image, ImageEnhance, ImageFilter
import io

log = logging.getLogger("nano-client")

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION   = os.getenv("GCP_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
SCOPES     = ["https://www.googleapis.com/auth/cloud-platform"]
MODEL_ID   = "gemini-2.5-flash-image-preview"
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
NANO_HTTP_TIMEOUT = int(os.getenv("NANO_HTTP_TIMEOUT", "180"))

def _load_credentials():
    js = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if js:
        info = json.loads(js)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if path and os.path.exists(path):
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise RuntimeError("No Google credentials (GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS)")

def _access_token() -> str:
    creds = _load_credentials()
    creds.refresh(Request())
    return creds.token


def _post_with_retry(url: str, headers: dict, payload: dict,
                     timeout: int = NANO_HTTP_TIMEOUT,
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
            log.warning("Nano request retry %s/%s after %s", attempt, attempts, last_error)
            time.sleep(min(20, sleep_for))

    raise RuntimeError(f"Nano request failed after {attempts} attempts: {last_error}")

def _enhance_gemini_image(image_bytes: bytes) -> bytes:
    """Улучшает качество изображения от Gemini: убирает шум, повышает резкость без потери деталей."""
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Легкое подавление шума
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        # Умеренное повышение резкости
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.15)  # Небольшое улучшение резкости
        
        # Легкое улучшение контраста
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.05)  # Минимальное улучшение контраста
        
        # Сохраняем в высоком качестве
        output = io.BytesIO()
        image.save(output, format='PNG', quality=95, optimize=True, compress_level=0)
        return output.getvalue()
        
    except Exception as e:
        log.warning("Failed to enhance Gemini image quality: %s", e)
        return image_bytes  # Возвращаем оригинал если не удалось улучшить

def repose_or_relocate(dressed_bytes: bytes, prompt: str = "", bg_bytes: bytes | None = None) -> bytes:
    """
    Берём уже ОДЕТУЮ модель (результат VTO) и просим Nano Banana слегка изменить позу/сцену.
    Это эксперимент: для стабильной «новой позы» лучше прислать новое фото человека в нужной позе
    и снова вызвать VTO.
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

    inst = []
    inst.append({
        "image": {"bytesBase64Encoded": base64.b64encode(dressed_bytes).decode("utf-8")}
    })
    if bg_bytes:
        inst.append({
            "image": {"bytesBase64Encoded": base64.b64encode(bg_bytes).decode("utf-8")}
        })

    instruction = (
        "Recompose the first image (already dressed person) with minimal identity drift. "
        "Keep the face and body proportions. Adjust pose/background according to the user description. "
        "Avoid text, watermarks and overlays. Output one realistic photo."
    )
    if prompt:
        instruction += " User description: " + prompt.strip()

    body = {
        "instances": inst + [{"prompt": instruction}],
        "parameters": {
            "sampleCount": 1,
            "resolution": "high",  # Высокое разрешение
            "quality": "high",  # Высокое качество
            "enhancement": "super_resolution",  # Супер-разрешение
            "noise_reduction": True,  # Подавление шума
            "sharpening": "medium"  # Умеренная резкость
        }
    }

    r = _post_with_retry(url, headers, body)
    data = r.json()
    pred = (data.get("predictions") or [{}])[0]
    b64 = pred.get("bytesBase64Encoded")
    if not b64:
        raise RuntimeError(f"Unexpected nano response: {data}")
    
    # Декодируем изображение и улучшаем качество
    result_bytes = base64.b64decode(b64)
    enhanced_bytes = _enhance_gemini_image(result_bytes)
    return enhanced_bytes
