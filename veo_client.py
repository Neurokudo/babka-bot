import os
import time
import json
import base64
import logging
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

log = logging.getLogger("veo_client")
logging.basicConfig(level=logging.INFO)

# Настройки
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ornate-producer-473220-g2")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

# Ключ для GCP
def _get_credentials():
    key_b64 = os.getenv("GCP_KEY_JSON_B64")
    if not key_b64:
        raise RuntimeError("GCP_KEY_JSON_B64 не задан")

    key_json = base64.b64decode(key_b64).decode("utf-8")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(key_json),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(Request())
    return creds


def _authorized_session():
    creds = _get_credentials()
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {creds.token}"})
    return session


def generate_video_sync(prompt: str, duration: int = 8, aspect_ratio: str = "9:16"):
    """
    Генерация видео через Veo 3 Fast
    """
    sess = _authorized_session()

    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL}:predictLongRunning"

    body = {
        "instances": [
            {"prompt": prompt}
        ],
        "parameters": {
            "sampleCount": 1,
            "resolution": "720p",
            "duration": f"{duration}s",
            "aspectRatio": aspect_ratio,
        },
    }

    log.info(f"Запрос генерации: {url}")
    r = sess.post(url, json=body)
    if r.status_code != 200:
        raise RuntimeError(f"Generation error {r.status_code}: {r.text}")

    resp = r.json()
    op_name = resp.get("name")
    if not op_name:
        raise RuntimeError(f"Не удалось получить operation name: {resp}")

    log.info(f"Получили op_name: {op_name}")

    return _poll(sess, op_name)


def _poll(sess, op_name: str):
    """
    Опрос состояния операции через fetchPredictOperation
    """
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL}:fetchPredictOperation"
    payload = {"name": op_name}

    log.info(f"Poll через fetchPredictOperation: {url} | payload={payload}")

    while True:
        r = sess.post(url, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"Poll error {r.status_code}: {r.text}")

        data = r.json()
        if data.get("done"):
            log.info("Операция завершена")
            return data

        time.sleep(5)

