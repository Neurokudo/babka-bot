# -*- coding: utf-8 -*-
"""
veo_client.py — клиент для Veo 3 через predictLongRunning + fetchPredictOperation
"""

import os, json, time, base64, pathlib, uuid, logging
from typing import Dict, Any, Optional, Tuple

log = logging.getLogger("veo_client")
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

PROJECT = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

# --------------------------------------------------------------------------
def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    js = os.getenv("GCP_KEY_JSON")
    b64 = os.getenv("GCP_KEY_JSON_B64")

    info = None
    if b64:
        info = json.loads(base64.b64decode(b64).decode("utf-8"))
    elif js:
        info = json.loads(js)

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds

def _authorized_session():
    import requests
    creds = _get_credentials()
    class Sess(requests.Session):
        def __init__(self, token: str):
            super().__init__()
            self.headers.update({"Authorization": f"Bearer {token}"})
    return Sess(creds.token)

# --------------------------------------------------------------------------
def generate_video_sync(prompt: str,
                        duration: int = 8,
                        aspect_ratio: str = "16:9",
                        filename_prefix: str = "veo_video") -> Dict[str, Any]:
    if not prompt:
        raise ValueError("Prompt is empty")

    sess = _authorized_session()
    model_name = f"projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}"
    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{model_name}:predictLongRunning"

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "duration": duration,
            "aspectRatio": aspect_ratio,
            "sampleCount": 1
        }
    }

    log.info("Запрос генерации: %s", endpoint)
    r = sess.post(endpoint, json=body, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Start error {r.status_code}: {r.text}")

    op_name = r.json().get("name")
    if not op_name:
        raise RuntimeError("Не получили operation.name")

    # poll через fetchPredictOperation
    poll_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{model_name}:fetchPredictOperation"
    log.info("Poll через fetchPredictOperation: %s", poll_url)

    deadline, interval = 600, 5
    t0 = time.time()
    while True:
        rr = sess.post(poll_url, json={"name": op_name}, timeout=60)
        if rr.status_code >= 300:
            raise RuntimeError(f"Poll error {rr.status_code}: {rr.text}")

        payload = rr.json()
        if payload.get("done"):
            break
        if time.time() - t0 > deadline:
            raise RuntimeError("Таймаут ожидания операции")
        time.sleep(interval)

    resp = payload.get("response", {})
    result = {}
    videos = resp.get("videos") or []
    if videos:
        # сохраняем первый ролик локально
        gcs_uri = videos[0].get("gcsUri")
        result["gcsUri"] = gcs_uri
        result["mimeType"] = videos[0].get("mimeType")
    else:
        raise RuntimeError(f"Нет videos в ответе: {json.dumps(resp)}")

    return result

