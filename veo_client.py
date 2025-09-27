import os
import time
import json
import logging
import base64
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

log = logging.getLogger("veo_client")

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "ornate-producer-473220-g2")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

# Чтение ключа из переменной окружения
def _load_credentials():
    key_b64 = os.getenv("GCP_KEY_JSON_B64")
    if not key_b64:
        raise RuntimeError("GCP_KEY_JSON_B64 не задан")
    key_json = base64.b64decode(key_b64).decode("utf-8")
    creds_info = json.loads(key_json)
    return service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

def _authorized_session():
    creds = _load_credentials()
    creds.refresh(Request())
    sess = requests.Session()
    sess.headers.update({
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json; charset=utf-8",
    })
    return sess

def generate_video_sync(prompt: str, duration: int = 8, aspect_ratio: str = "9:16"):
    """
    Синхронная генерация видео через Veo 3 Fast
    """
    sess = _authorized_session()

    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}:predictLongRunning"
    )

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "resolution": "720p",
            "durationSeconds": duration,
            "aspectRatio": aspect_ratio,
        },
    }

    log.info("Запрос генерации: %s", url)
    r = sess.post(url, json=body, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Generation error {r.status_code}: {r.text}")

    resp = r.json()
    op_name = resp.get("name")
    if not op_name:
        raise RuntimeError(f"Нет operation name в ответе: {resp}")

    log.info("Получили op_name: %s", op_name)

    # polling через fetchPredictOperation
    poll_url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/{op_name}:fetchPredictOperation"
    )
    log.info("Poll через fetchPredictOperation: %s", poll_url)

    deadline, interval = 600, 5
    t0 = time.time()
    while True:
        rr = sess.post(poll_url, timeout=60)  # 👈 без json
        if rr.status_code >= 300:
            raise RuntimeError(f"Poll error {rr.status_code}: {rr.text}")

        payload = rr.json()
        if payload.get("done"):
            return payload
        if time.time() - t0 > deadline:
            raise RuntimeError("Таймаут ожидания операции")
        time.sleep(interval)

