# -*- coding: utf-8 -*-
"""
veo_client.py — безопасный клиент Veo 3 (REST + Long-Running Operation).
Встроены fallback'и и подробные логи для отладки.
"""

import os, json, time, uuid, base64, pathlib, logging
from typing import Dict, Any, Optional, Tuple

log = logging.getLogger("veo_client")
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

PROJECT = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip() or "us-central1"
MODEL_ID = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001").strip()

# ----------------------------- Credentials helper -----------------------------
def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.auth.exceptions import DefaultCredentialsError

    js = os.getenv("GCP_KEY_JSON")
    b64 = os.getenv("GCP_KEY_JSON_B64")

    info = None
    if b64:
        try:
            info = json.loads(base64.b64decode(b64).decode("utf-8"))
        except Exception as e:
            log.warning("Не удалось декодировать GCP_KEY_JSON_B64: %s", e)
    if not info and js:
        try:
            info = json.loads(js)
        except Exception as e:
            log.warning("Не удалось распарсить GCP_KEY_JSON: %s", e)

    if not info:
        raise DefaultCredentialsError("Нет кредов: добавь GCP_KEY_JSON_B64 или GCP_KEY_JSON")

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def _authorized_session():
    import requests
    from google.auth.transport.requests import Request
    creds = _get_credentials()
    if not creds.valid:
        creds.refresh(Request())

    class _Sess(requests.Session):
        def __init__(self, token: str):
            super().__init__()
            self.headers.update({"Authorization": f"Bearer {token}"})
    return _Sess(creds.token)


# ------------------------------ Main API --------------------------------------
def generate_video_sync(prompt: str, duration: int = 8, aspect_ratio: str = "16:9", filename_prefix="veo_video") -> Dict[str, Any]:
    if not prompt:
        raise ValueError("prompt must be non-empty string")

    model_name = f"projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}"
    log.info("Запуск Veo LRO | model=%s | project=%s | location=%s", MODEL_ID, PROJECT, LOCATION)

    sess = _authorized_session()
    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{model_name}:predictLongRunning"
    body = {"instances": [{"prompt": prompt.strip()}],
            "parameters": {"aspectRatio": aspect_ratio, "duration": duration, "sampleCount": 1, "seed": 0}}

    r = sess.post(endpoint, json=body, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Ошибка запуска Veo: {r.status_code} {r.text}")

    op_name = r.json().get("name")
    if not op_name:
        raise RuntimeError("Не получили name операции от Veo.")

    log.info("Получили op_name: %s", op_name)
    op_id = op_name.split("/")[-1]

    # --- Попытка 1: global operations ---
    global_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/operations/{op_id}"
    log.info("Пробую poll global ops: %s", global_url)

    payload = _poll(sess, global_url)
    if not payload:
        # --- Попытка 2: полный путь ---
        alt_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{op_name}"
        log.warning("Global ops дал 404. Пробую poll по полному пути: %s", alt_url)
        payload = _poll(sess, alt_url)

    if not payload:
        raise RuntimeError(
            f"Poll не удался ни по global, ни по full op_name.\n"
            f"Проверь:\n"
            f"- GOOGLE_CLOUD_LOCATION={LOCATION}\n"
            f"- PROJECT={PROJECT}\n"
            f"- VEO_MODEL={MODEL_ID}\n"
            f"- Роли сервис-аккаунта (Vertex AI User)\n"
        )

    # --- результат ---
    resp = payload.get("response") or {}
    uri, file_bytes = _extract_video_from_operation_response(resp)
    result = {}
    if file_bytes:
        out_dir = pathlib.Path("/app/output"); out_dir.mkdir(parents=True, exist_ok=True)
        fpath = out_dir / f"{filename_prefix}_{int(time.time())}.mp4"
        fpath.write_bytes(file_bytes)
        result["file_path"] = str(fpath)
    if uri:
        result["uri"] = uri
    return result


def _poll(sess, url: str, deadline: int = 600, interval: int = 5) -> Optional[Dict[str, Any]]:
    t0 = time.time()
    while True:
        r = sess.get(url, timeout=60)
        if r.status_code == 404:
            return None
        if r.status_code >= 300:
            raise RuntimeError(f"Vertex poll error {r.status_code}: {r.text}")
        payload = r.json()
        if payload.get("done"):
            return payload
        if time.time() - t0 > deadline:
            raise RuntimeError("Таймаут ожидания операции Veo.")
        time.sleep(interval)


def _extract_video_from_operation_response(resp: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
    uri, file_bytes = None, None
    try:
        outputs = resp.get("outputs") or []
        if outputs and isinstance(outputs, list):
            out0 = outputs[0] or {}
            uri = out0.get("fileUri") or out0.get("videoUri")
            b64 = out0.get("bytesBase64Encoded") or out0.get("videoBytesBase64")
            if b64:
                file_bytes = base64.b64decode(b64)
    except Exception as e:
        log.warning("Ошибка парсинга ответа Veo: %s", e)
    return uri, file_bytes
