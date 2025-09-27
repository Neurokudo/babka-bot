# -*- coding: utf-8 -*-
"""
veo_client.py — простой клиент Veo 3 на Vertex AI (REST + Long‑Running Operation)

- Только REST.
- Модель: VEO_MODEL (по умолчанию "veo-3.0-fast-generate-001")
- Старт через :predictLongRunning, опрос через global operations:
  projects/{project}/locations/{location}/operations/{operationId}
- Креды из ENV: GCP_KEY_JSON_B64 (base64) или GCP_KEY_JSON (one-line JSON).
- Автоповторы при 429/RESOURCE_EXHAUSTED и опциональный локальный rate limit.

ENV:
  GCP_KEY_JSON_B64 | GCP_KEY_JSON
  GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID
  GOOGLE_CLOUD_LOCATION=us-central1
  VEO_MODEL=veo-3.0-fast-generate-001
  (опц.) VEO_RETRIES=6, VEO_BACKOFF_BASE=4, VEO_BACKOFF_MULT=1.8, VEO_BACKOFF_MAX=45
  (опц.) VEO_POLL_DEADLINE=600, VEO_POLL_INTERVAL=5, VEO_RATE_LIMIT_SECONDS=0
"""

from __future__ import annotations

import os
import json
import time
import uuid
import base64
import pathlib
import logging
from typing import Dict, Any, Optional, Tuple

log = logging.getLogger("veo_client")
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

PROJECT: str = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip() or "us-central1"
MODEL_ID: str = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001").strip() or "veo-3.0-fast-generate-001"


# ----------------------------- Credentials helper -----------------------------
def _get_credentials():
    """Возвращает google.oauth2.service_account.Credentials из ENV."""
    from google.auth.transport.requests import Request  # type: ignore
    from google.oauth2 import service_account  # type: ignore
    from google.auth.exceptions import DefaultCredentialsError  # type: ignore

    js = os.getenv("GCP_KEY_JSON")
    b64 = os.getenv("GCP_KEY_JSON_B64")

    info = None
    if b64:
        try:
            data = base64.b64decode(b64).decode("utf-8")
            info = json.loads(data)
        except Exception as e:
            log.warning("Не удалось декодировать GCP_KEY_JSON_B64: %s", e)

    if not info and js:
        try:
            info = json.loads(js)
        except Exception as e:
            log.warning("Не удалось распарсить GCP_KEY_JSON: %s", e)

    if not info:
        raise DefaultCredentialsError("Нет кредов: добавь GCP_KEY_JSON_B64 (base64) или GCP_KEY_JSON (one-line).")

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def _authorized_session():
    """requests.Session с Authorization: Bearer <token>."""
    import requests  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore

    creds = _get_credentials()
    if not creds.valid:
        creds.refresh(Request())

    class _Sess(requests.Session):
        def __init__(self, token: str):
            super().__init__()
            self.headers.update({"Authorization": f"Bearer {token}"})
    return _Sess(creds.token)


# ------------------------------ Retry helper ----------------------------------
def _post_with_retries(sess, url, json_body, *,
                       timeout=60,
                       max_retries:int=int(os.getenv("VEO_RETRIES", "6")),
                       base_sleep:float=float(os.getenv("VEO_BACKOFF_BASE", "4")),
                       multiplier:float=float(os.getenv("VEO_BACKOFF_MULT", "1.8")),
                       max_sleep:float=float(os.getenv("VEO_BACKOFF_MAX", "45"))):
    """
    Делает POST с экспоненциальным бэк-оффом при 429/RESOURCE_EXHAUSTED/503.
    """
    import time as _t, random
    last = None
    for attempt in range(max_retries):
        r = sess.post(url, json=json_body, timeout=timeout)
        last = r
        need_retry = False
        if r.status_code in (429, 503):
            need_retry = True
        else:
            try:
                j = r.json()
                err = (j.get("error") or {})
                if err.get("status") in ("RESOURCE_EXHAUSTED",) or "quota" in (err.get("message","").lower()):
                    need_retry = True
            except Exception:
                pass
        if not need_retry:
            return r
        sleep_s = min(base_sleep * (multiplier ** attempt), max_sleep)
        sleep_s += random.uniform(0, 0.5)
        try:
            log.warning("Quota/429 (attempt %d/%d). Сплю %.1fs и повторяю…", attempt+1, max_retries, sleep_s)
        except Exception:
            pass
        _t.sleep(sleep_s)
    return last


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
    REST-вызов Veo 3 через predictLongRunning + опрос global operations.
    Возвращает dict с "file_path" и/или "uri".
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")

    model_name = _make_model_name(PROJECT, LOCATION, MODEL_ID)
    log.info("VEO LRO start | model=%s | project=%s | location=%s | duration=%ss | AR=%s",
             MODEL_ID, PROJECT, LOCATION, duration, aspect_ratio)

    # Опциональный local rate limit
    _rate_limit = float(os.getenv("VEO_RATE_LIMIT_SECONDS", "0"))
    if _rate_limit > 0:
        import time as _rt, os as _os
        _stamp_file = "/tmp/veo_last_start"
        try:
            last_t = 0.0
            if _os.path.exists(_stamp_file):
                with open(_stamp_file, "r") as fh:
                    last_t = float(fh.read().strip() or "0")
            now = _rt.time()
            delta = now - last_t
            if delta < _rate_limit:
                sleep_need = _rate_limit - delta
                log.info("Local rate limit: сплю %.2fs", sleep_need)
                _rt.sleep(sleep_need)
            with open(_stamp_file, "w") as fh:
                fh.write(str(_rt.time()))
        except Exception:
            pass

    # 1) Запускаем операцию
    sess = _authorized_session()
    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{model_name}:predictLongRunning"
    body = {
        "instances": [
            {
                "prompt": prompt.strip()
            }
        ],
        "parameters": {
            "aspectRatio": aspect_ratio,     # "16:9" | "9:16"
            "duration": duration,            # секунды
            "sampleCount": 1,
            "seed": 0
        }
    }

    r = _post_with_retries(sess, endpoint, body, timeout=60)
    if r.status_code == 404:
        raise RuntimeError(
            f"404 Model not found. Проверь GOOGLE_CLOUD_LOCATION='{LOCATION}' "
            f"и VEO_MODEL='{MODEL_ID}'. Поддерживаются: "
            f"'veo-3.0-generate-001', 'veo-3.0-fast-generate-001' (регион us-central1)."
        )
    if r.status_code >= 300:
        try:
            err_payload = r.json()
        except Exception:
            err_payload = r.text
        raise RuntimeError(f"Vertex start error {r.status_code}: {err_payload}")

    op_name = r.json().get("name")
    if not op_name:
        raise RuntimeError("Не получили имя операции от Veо (ожидали long-running).")

    # 2) Поллинг: global operations (НЕ под моделью!)
    # name может прийти как полный путь с /models/.../operations/{id} — берём operationId
    if "/operations/" in op_name:
        op_id = op_name.split("/operations/")[-1].strip()
    else:
        op_id = op_name.strip()

    op_path = f"projects/{PROJECT}/locations/{LOCATION}/operations/{op_id}"
    op_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{op_path}"

    deadline_s = int(os.getenv("VEO_POLL_DEADLINE", "600"))
    interval_s = int(os.getenv("VEO_POLL_INTERVAL", "5"))
    t0 = time.time()
    while True:
        rr = sess.get(op_url, timeout=60)
        if rr.status_code == 404 and "/models/" in op_name:
            # fallback: попробуем опросить ровно тот путь, который вернул старт
            alt_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{op_name}"
            rr = sess.get(alt_url, timeout=60)
        if rr.status_code >= 300:
            try:
                errp = rr.json()
            except Exception:
                errp = rr.text
            raise RuntimeError(f"Vertex poll error {rr.status_code}: {errp}")

        payload = rr.json()
        if payload.get("done"):
            break
        if (time.time() - t0) > deadline_s:
            raise RuntimeError("Таймаут ожидания Veo операции.")
        time.sleep(interval_s)

    # 3) Результат
    resp = payload.get("response") or payload.get("result") or {}
    uri, file_bytes = _extract_video_from_operation_response(resp)

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
        raise RuntimeError("Операция завершилась без URI/bytes. Проверь ответ Veo.")

    log.info("VEO LRO done | %s", result)
    return result


# ------------------------------ Parsers ---------------------------------------
def _extract_video_from_operation_response(resp: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
    """Ищем видео в структуре ответа LRO."""
    uri = None
    file_bytes = None

    try:
        outputs = resp.get("outputs") or resp.get("predictions") or []
        if outputs and isinstance(outputs, list):
            out0 = outputs[0] or {}
            if isinstance(out0, dict):
                uri = out0.get("fileUri") or out0.get("videoUri") or uri
                b64 = out0.get("bytesBase64Encoded") or out0.get("videoBytesBase64")
                if b64 and not file_bytes:
                    try:
                        file_bytes = base64.b64decode(b64)
                    except Exception:
                        pass
                v = out0.get("video")
                if isinstance(v, dict):
                    uri = v.get("fileUri") or uri
                    b64 = v.get("bytesBase64Encoded") or v.get("data")
                    if b64 and not file_bytes:
                        try:
                            file_bytes = base64.b64decode(b64)
                        except Exception:
                            pass
    except Exception as e:
        log.debug("parse LRO response error: %s", e)

    return uri, file_bytes
