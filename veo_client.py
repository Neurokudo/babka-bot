# -*- coding: utf-8 -*-
"""
veo_client.py — обёртка для генерации видео в Google Vertex AI (Veo 3)

ENV (Railway / Docker):
- GCP_PROJECT_ID         (или GOOGLE_CLOUD_PROJECT) — id проекта
- GOOGLE_CLOUD_LOCATION  — регион, по умолчанию us-central1  (для Veo это правильный регион)
- VEO_MODEL              — "veo-3.0-fast" (по умолчанию) или "veo-3.0"
- GOOGLE_APPLICATION_CREDENTIALS — (необязательно) путь к JSON ключу
  * если вы кладёте ключ в переменную GCP_KEY_JSON_B64 и пишете его на диск в main.py,
    то просто выставьте GOOGLE_APPLICATION_CREDENTIALS=/app/gcp.json

Требуемые зависимости (requirements.txt):
- google-auth
- google-auth-oauthlib
- google-cloud-aiplatform>=1.66.0
- vertexai>=1.66.0
- requests

Функции:
- generate_video_sync(prompt: str, duration: int = 8, aspect_ratio: str = "16:9") -> dict
  Возвращает словарь: {"file_path": "/app/output/...", "uri": "..."} — одно из полей точно будет.
"""

from __future__ import annotations

import os
import io
import json
import time
import uuid
import pathlib
import logging
from typing import Optional, Tuple, Dict, Any

# --- Логирование --------------------------------------------------------------
log = logging.getLogger("veo_client")
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

# --- ENV ----------------------------------------------------------------------
PROJECT: str = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip() or "us-central1"
MODEL_ID: str = os.getenv("VEO_MODEL", "veo-3.0-fast").strip() or "veo-3.0-fast"

if not PROJECT:
    log.warning("GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID не задан — SDK может упасть на init().")

# --- SDK импорты (ленивые) ----------------------------------------------------
_vertexai_loaded = False
def _lazy_import_vertexai():
    global _vertexai_loaded
    if _vertexai_loaded:
        return
    try:
        # В новых версиях всё в vertexai.*, а GenerativeModel доступен также в preview.
        import vertexai  # type: ignore
        try:
            from vertexai.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        except Exception:
            # на случай, если дистрибутив держит preview-путь
            from vertexai.preview.generative_models import GenerativeModel, GenerationConfig  # type: ignore
        _vertexai_loaded = True
        return vertexai, GenerativeModel, GenerationConfig
    except Exception as e:
        log.warning("Не удалось импортировать vertexai SDK: %s", e)
        raise

# --- Auth / REST --------------------------------------------------------------
def _authorized_session():
    """Возвращает авторизованный requests.Session через google-auth."""
    import requests  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
    import google.auth  # type: ignore

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid:
        creds.refresh(Request())

    class _AuthSess(requests.Session):  # маленькая обёртка, чтобы всегда проставлять Bearer
        def __init__(self, token: str):
            super().__init__()
            self.headers.update({"Authorization": f"Bearer {token}"})

    return _AuthSess(creds.token)

def _make_model_name(project: str, location: str, model_id: str) -> str:
    """
    Корректный путь к модели ПУБЛИШЕРА (без -generate-preview):
    projects/{project}/locations/{location}/publishers/google/models/{model_id}
    """
    return f"projects/{project}/locations/{location}/publishers/google/models/{model_id}"

def _ensure_output_dir() -> pathlib.Path:
    out_dir = pathlib.Path(os.getenv("OUTPUT_DIR", "/app/output")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

# --- Основная функция ---------------------------------------------------------
def generate_video_sync(
    prompt: str,
    duration: int = 8,
    aspect_ratio: str = "16:9",
    filename_prefix: str = "veo_video"
) -> Dict[str, Any]:
    """
    Генерация видео. Пытаемся сначала через vertexai SDK, если не вышло — через REST.
    Возвращает {"file_path": "..."} ИЛИ {"uri": "..."} (может вернуть оба).
    Бросает исключение при фатальной ошибке.
    """

    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")

    model_name = _make_model_name(PROJECT, LOCATION, MODEL_ID)
    log.info("VEO generate start | model=%s | project=%s | location=%s | duration=%ss | AR=%s",
             MODEL_ID, PROJECT, LOCATION, duration, aspect_ratio)

    # 1) Попытка через vertexai SDK
    try:
        vertexai, GenerativeModel, GenerationConfig = _lazy_import_vertexai()
        vertexai.init(project=PROJECT, location=LOCATION)

        gen_config = GenerationConfig(
            # Параметры могут игнорироваться сервером, но не вредят
            response_mime_type="application/json"
        )

        model = GenerativeModel(MODEL_ID)  # Важно: без "-generate-preview"
        # Многие билды Veo ожидают «специальный» блок с параметрами видео.
        # Передадим duration и aspect_ratio внутрь текста — это надёжно для разных версий.
        composed_prompt = f"{prompt.strip()}\n\nDuration: {duration}s\nAspect Ratio: {aspect_ratio}\nClear video without text."

        resp = model.generate_content(
            [composed_prompt],
            generation_config=gen_config,
            # stream=False — по умолчанию
        )

        # Унифицированный парсинг ответа
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

        if not result:
            # Если SDK не отдал ничего — попробуем REST.
            log.warning("SDK ответ без файла/URI, пробую REST путь...")
            return _generate_via_rest(prompt, duration, aspect_ratio, filename_prefix)

        log.info("VEO generate done via SDK | %s", result)
        return result

    except Exception as e:
        log.warning("SDK способ не сработал (%s). Пытаюсь REST…", e)

    # 2) Фолбэк: REST
    return _generate_via_rest(prompt, duration, aspect_ratio, filename_prefix)

# --- REST путь ----------------------------------------------------------------
def _generate_via_rest(
    prompt: str,
    duration: int,
    aspect_ratio: str,
    filename_prefix: str
) -> Dict[str, Any]:
    """
    Вызов REST API Vertex AI: POST .../generateContent
    """
    import requests  # type: ignore

    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{_make_model_name(PROJECT, LOCATION, MODEL_ID)}:generateContent"
    sess = _authorized_session()

    # Формируем "contents" по протоколу Gemini/Veo
    # С учётом разношёрстности реализаций проще передать duration/AR внутри текста.
    composed_prompt = f"{prompt.strip()}\n\nDuration: {duration}s\nAspect Ratio: {aspect_ratio}\nClear video without text."
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
        # Частая причина: не тот регион или кривой ID модели
        raise RuntimeError(
            f"404 Model not found. Проверь GOOGLE_CLOUD_LOCATION='{LOCATION}' "
            f"и VEO_MODEL='{MODEL_ID}'. Для Veo используйте us-central1 и 'veo-3.0(-fast)'."
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
        raise RuntimeError("Не удалось извлечь видео из REST ответа (нет URI/bytes).")

    log.info("VEO generate done via REST | %s", result)
    return result

# --- Вспомогательный парсинг ответов -----------------------------------------
def _extract_video_from_response(resp) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Пытается вытащить URI или байты из ответа SDK.
    Возвращает (uri, bytes) — одно из полей может быть None.
    """
    uri = None
    file_bytes = None

    try:
        # Универсальный способ для vertexai: пройтись по candidates/parts
        candidates = getattr(resp, "candidates", []) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", []) or []
            for p in parts:
                # варианты: p.file_data.file_uri, p.inline_data.data
                fdata = getattr(p, "file_data", None)
                if fdata and getattr(fdata, "file_uri", None):
                    uri = fdata.file_uri
                idata = getattr(p, "inline_data", None)
                if idata and getattr(idata, "data", None):
                    try:
                        import base64
                        file_bytes = base64.b64decode(idata.data)
                    except Exception:
                        pass
        # Иногда SDK кладёт ссылки ещё и в resp.media или resp._raw_response — на всякий
        if not uri and hasattr(resp, "media"):
            media = getattr(resp, "media", None)
            if isinstance(media, dict) and "fileUri" in media:
                uri = media["fileUri"]
    except Exception as e:
        log.debug("parse SDK response error: %s", e)

    return uri, file_bytes


def _extract_video_from_rest_payload(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Пытается вытащить URI или байты из REST-ответа Gemini/Veo.
    Возвращает (uri, bytes).
    """
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

        # Иногда REST кладёт медиа прямо в top-level
        if not uri:
            maybe_uri = payload.get("fileUri") or payload.get("media", {}).get("fileUri")
            if maybe_uri:
                uri = maybe_uri
    except Exception as e:
        log.debug("parse REST payload error: %s", e)

    return uri, file_bytes

