# -*- coding: utf-8 -*-
"""
veo_client.py — финальный клиент Veo 3 (REST + Long‑Running Operation).

Особенности:
- Использует :predictLongRunning
- Поллинг строго по полному `op_name`, который вернул Veo (с publishers/google/models/.../operations/uuid)
- Креды: GCP_KEY_JSON_B64 (base64) или GCP_KEY_JSON (one-line JSON)
- Поддержка автоповторов при 429/RESOURCE_EXHAUSTED
- Опциональный локальный rate limit между запросами
"""

import os, json, time, uuid, base64, pathlib, logging
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
        log.warning("Quota/429 (attempt %d/%d). Сплю %.1fs и повторяю…", attempt+1, max_retries, sleep_s)
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
    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")

    model_name = _make_model_name(PROJECT, LOCATION, MODEL_ID)
    log.info("VEO LRO start | model=%s | project=%s | location=%s | duration=%ss | AR=%s",
             MODEL_ID, PROJECT, LOCATION, duration, aspect_ratio)

    # Local rate limit
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

    sess = _authorized_session()
    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{model_name}:predictLongRunning"
    body = {
        "instances": [{"prompt": prompt.strip()}],
        "parameters": {
            "aspectRatio": aspect_ratio,
            "duration": duration,
            "sampleCount": 1,
            "seed": 0
        }
    }

    r = _post_with_retries(sess, endpoint, body, timeout=60)
    if r.status_code == 404:
        raise RuntimeError(f"404 Model not found. Проверь GOOGLE_CLOUD_LOCATION='{LOCATION}' и VEO_MODEL='{MODEL_ID}'.")
    if r.status_code >= 300:
        try:
            err_payload = r.json()
        except Exception:
            err_payload = r.text
        raise RuntimeError(f"Vertex start error {r.status_code}: {err_payload}")

    op_name = r.json().get("name")
    if not op_name:
        raise RuntimeError("Не получили имя операции от Veo (ожидали long-running).")

    # Поллинг строго по полному пути
    op_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{op_name}"
    log.info("Polling full op_name: %s", op_url)

    deadline_s = int(os.getenv("VEO_POLL_DEADLINE", "600"))
    interval_s = int(os.getenv("VEO_POLL_INTERVAL", "5"))
    t0 = time.time()
    while True:
        rr = sess.get(op_url, timeout=60)
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
