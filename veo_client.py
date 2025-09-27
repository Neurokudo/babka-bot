# -*- coding: utf-8 -*-
"""
veo_client.py — обёртка для генерации видео в Google Vertex AI (Veo 3)

Что я упростил:
- Больше НЕ нужен GOOGLE_APPLICATION_CREDENTIALS и ADC.
- Клиент сам берёт ключ из ENV: GCP_KEY_JSON (однострочный JSON) или GCP_KEY_JSON_B64.
- Работает и через vertexai SDK, и через REST (фолбэк).
- Вернёт dict: {"file_path": "...", "uri": "..."}. Хотя бы одно поле будет.

ENV (Railway):
- GCP_KEY_JSON (Shared Variable, one-line JSON) ИЛИ GCP_KEY_JSON_B64 (base64 того же JSON).
- GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID = id проекта
- GOOGLE_CLOUD_LOCATION = us-central1
- VEO_MODEL = "veo-3.0-fast" или "veo-3.0"

requirements.txt должен содержать:
google-auth
google-cloud-aiplatform>=1.66.0
vertexai>=1.66.0
requests
"""

from __future__ import annotations

import os
import json
import time
import uuid
import pathlib
import logging
from typing import Optional, Tuple, Dict, Any

log = logging.getLogger("veo_client")
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

PROJECT: str = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip() or "us-central1"
MODEL_ID: str = os.getenv("VEO_MODEL", "veo-3.0-fast").strip() or "veo-3.0-fast"


# ----------------------------- Credentials helper -----------------------------
def _get_credentials():
    """
    Возвращает google.auth.credentials.Credentials.

    Порядок:
    1) Пытается Application Default Credentials (если выставлен GOOGLE_APPLICATION_CREDENTIALS).
    2) Если нет — берёт сервисный ключ из ENV:
       - GCP_KEY_JSON_B64 (base64-строка JSON-ключа)
       - GCP_KEY_JSON (однострочный JSON-ключ)
    """
    from google.auth.transport.requests import Request  # type: ignore
    import google.auth  # type: ignore
    from google.auth.exceptions import DefaultCredentialsError  # type: ignore
    from google.oauth2 import service_account  # type: ignore
    import base64

    # (1) ADC (если настроен)
    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not creds.valid:
            creds.refresh(Request())
        return creds
    except DefaultCredentialsError:
        pass

    # (2) Service Account из ENV (base64)
    raw = os.getenv("GCP_KEY_JSON_B64")
    if raw:
        try:
            data = base64.b64decode(raw).decode("utf-8")
            info = json.loads(data)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            if not creds.valid:
                creds.refresh(Request())
            return creds
        except Exception as e:
            log.warning("Не удалось разобрать GCP_KEY_JSON_B64: %s", e)

    # (3) Service Account из ENV (one-line JSON)
    raw = os.getenv("GCP_KEY_JSON")
    if raw:
        try:
            info = json.loads(raw)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            if not creds.valid:
                creds.refresh(Request())
            return creds
        except Exception as e:
            log.warning("Не удалось разобрать GCP_KEY_JSON: %s", e)

    raise DefaultCredentialsError("Нет кредитов: ни ADC, ни GCP_KEY_JSON(_B64).")


# ----------------------------- SDK (lazy import) ------------------------------
_vertexai_loaded = False
def _lazy_import_vertexai():
    """Лениво импортируем vertexai и модели (совместимо с preview)."""
    global _vertexai_loaded
    if _vertexai_loaded:
        import vertexai  # type: ignore
        try:
            from vertexai.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        except Exception:
            from vertexai.preview.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        return vertexai, GenerativeModel, GenerationConfig

    try:
        import vertexai  # type: ignore
        try:
            from vertexai.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        except Exception:
            from vertexai.preview.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        _vertexai_loaded = True
        return vertexai, GenerativeModel, GenerationConfig
    except Exception as e:
        log.warning("Не удалось импортировать vertexai SDK: %s", e)
        raise


# ----------------------------- REST auth session ------------------------------
def _authorized_session():
    """Возвращает requests.Session с Authorization: Bearer <token>."""
    import requests  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore

    creds = _get_credentials()
    if not creds.valid:
        creds.refresh(Request())

    class _AuthSess(requests.Session):
        def __init__(self, token: str):
            super().__init__()
            self.headers.update({"Authorization": f"Bearer {token}"})

    return _AuthSess(creds.token)


# --------------------------------- Utilities ----------------------------------
def _make_model_name(project: str, location: str, model_id: str) -> str:
    return f"projects/{project}/locations/{location}/publishers/google/models/{model_id}"

def _ensure_output_dir() -> pathlib.Path:
    out_dir = pathlib.Path(os.getenv("OUTPUT_DIR", "/app/output")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# --------------------------------- Public API ---------------------------------
def generate_video_sync(
    prompt: str,
    duration: int = 8,
    aspect_ratio: str = "16:9",
    filename_prefix: str = "veo_video"
) -> Dict[str, Any]:
    """
    Генерация видео. Сначала пробуем через vertexai SDK (с кредами из ENV),
    если не получилось — фолбэк на REST. Возвращает dict с file_path и/или uri.
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")

    model_name = _make_model_name(PROJECT, LOCATION, MODEL_ID)
    log.info(
        "VEO generate start | model=%s | project=%s | location=%s | duration=%ss | AR=%s",
        MODEL_ID, PROJECT, LOCATION, duration, aspect_ratio
    )

    # --- SDK путь ---
    try:
        vertexai, GenerativeModel, GenerationConfig = _lazy_import_vertexai()
        creds = _get_credentials()
        vertexai.init(project=PROJECT, location=LOCATION, credentials=creds)

        gen_config = GenerationConfig(response_mime_type="application/json")
        model = GenerativeModel(MODEL_ID)  # ВАЖНО: без суффикса "-generate-preview"

        composed_prompt = (
            f"{prompt.strip()}\n\n"
            f"Duration: {duration}s\n"
            f"Aspect Ratio: {aspect_ratio}\n"
            f"Clear video without text."
        )

        resp = model.generate_content([composed_prompt], generation_config=gen_config)

        uri, file_bytes = _extract_video_from_response(resp)
        result: Dict[str, Any] = {}
        if file_bytes:
            out_dir = _ensure_output_dir()
            fname = f"{filename_prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
            fpath = out_dir / fname
            with open(fpath, "wb") as f:
                f.write(file_bytes)
            result["file_path"] = str(fpath)
        if uri:
            result["uri"] = uri

        if result:
            log.info("VEO generate done via SDK | %s", result)
            return result
        else:
            log.warning("SDK ответ без файла/URI, пробую REST...")
            return _generate_via_rest(prompt, duration, aspect_ratio, filename_prefix)

    except Exception as e:
        log.warning("SDK способ не сработал (%s). Пытаюсь REST…", e)

    # --- REST путь ---
    return _generate_via_rest(prompt, duration, aspect_ratio, filename_prefix)


# ---------------------------------- REST path ---------------------------------
def _generate_via_rest(
    prompt: str,
    duration: int,
    aspect_ratio: str,
    filename_prefix: str
) -> Dict[str, Any]:
    import requests  # type: ignore

    endpoint = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/"
        f"{_make_model_name(PROJECT, LOCATION, MODEL_ID)}:generateContent"
    )
    sess = _authorized_session()

    composed_prompt = (
        f"{prompt.strip()}\n\n"
        f"Duration: {duration}s\n"
        f"Aspect Ratio: {aspect_ratio}\n"
        f"Clear video without text."
    )
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": composed_prompt}]
            }
        ]
    }

    r = sess.post(endpoint, json=body, timeout=600)
    if r.status_code == 404:
        raise RuntimeError(
            f"404 Model not found. Проверь GOOGLE_CLOUD_LOCATION='{LOCATION}' "
            f"и VEO_MODEL='{MODEL_ID}'. Для Veo используй us-central1 и 'veo-3.0(-fast)'."
        )
    if r.status_code >= 300:
        try:
            err_payload = r.json()
        except Exception:
            err_payload = r.text
        raise RuntimeError(f"Vertex REST error {r.status_code}: {err_payload}")

    payload = r.json()
    uri, file_bytes = _extract_video_from_rest_payload(payload)

    result: Dict[str, Any] = {}
    if file_bytes:
        out_dir = _ensure_output_dir()
        fname = f"{filename_prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
        fpath = out_dir / fname
        with open(fpath, "wb") as f:
            f.write(file_bytes)
        result["file_path"] = str(fpath)
    if uri:
        result["uri"] = uri

    if not result:
        raise RuntimeError("Не удалось извлечь видео из REST-ответа (нет URI/bytes).")

    log.info("VEO generate done via REST | %s", result)
    return result


# -------------------------- Response parsers (SDK/REST) -----------------------
def _extract_video_from_response(resp) -> Tuple[Optional[str], Optional[bytes]]:
    """Пытается вытащить URI или байты из ответа SDK."""
    uri = None
    file_bytes = None

    try:
        candidates = getattr(resp, "candidates", []) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", []) or []
            for p in parts:
                fdata = getattr(p, "file_data", None)
                if fdata and getattr(fdata, "file_uri", None):
                    uri = fdata.file_uri
                idata = getattr(p, "inline_data", None)
                if idata and getattr(idata, "data", None):
                    import base64
                    try:
                        file_bytes = base64.b64decode(idata.data)
                    except Exception:
                        pass

        if not uri and hasattr(resp, "media"):
            media = getattr(resp, "media", None)
            if isinstance(media, dict) and "fileUri" in media:
                uri = media["fileUri"]
    except Exception as e:
        log.debug("parse SDK response error: %s", e)

    return uri, file_bytes


def _extract_video_from_rest_payload(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
    """Пытается вытащить URI или байты из REST-ответа Gemini/Veo."""
    uri = None
    file_bytes = None

    try:
        candidates = (payload.get("candidates") or [])
        for cand in candidates:
            content = cand.get("content") or {}
            parts = content.get("parts") or []
            for p in parts:
                if "fileData" in p and isinstance(p["fileData"], dict):
                    uri = p["fileData"].get("fileUri") or uri
                if "inlineData" in p and isinstance(p["inlineData"], dict):
                    data_b64 = p["inlineData"].get("data")
                    if data_b64:
                        import base64
                        try:
                            file_bytes = base64.b64decode(data_b64)
                        except Exception:
                            pass

        if not uri:
            maybe_uri = payload.get("fileUri") or payload.get("media", {}).get("fileUri")
            if maybe_uri:
                uri = maybe_uri
    except Exception as e:
        log.debug("parse REST payload error: %s", e)

    return uri, file_bytes
