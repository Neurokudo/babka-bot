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

# Дополнительная опция: качать mp4 локально?
DOWNLOAD = os.getenv("DOWNLOAD_VIDEOS", "0") == "1"

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
        "instances": [{"prompt": prompt}],
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
    payload = {"operationName": op_name}  # <-- исправлено

    log.info(f"Poll через fetchPredictOperation: {url} | payload={payload}")

    while True:
        r = sess.post(url, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"Poll error {r.status_code}: {r.text}")

        data = r.json()
        if data.get("done"):
            log.info("Операция завершена")

            # Извлекаем ссылки на видео
            videos = data.get("response", {}).get("videos", [])
            out_files = []
            for i, v in enumerate(videos):
                gcs_uri = v.get("gcsUri")
                if not gcs_uri:
                    continue

                item = {"uri": gcs_uri}

                # Если включена опция DOWNLOAD
                if DOWNLOAD:
                    try:
                        from google.cloud import storage
                        storage_client = storage.Client(project=PROJECT_ID, credentials=_get_credentials())

                        # Парсим bucket и путь
                        assert gcs_uri.startswith("gs://")
                        _, path = gcs_uri.split("gs://", 1)
                        bucket_name, blob_name = path.split("/", 1)

                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(blob_name)

                        local_path = f"video_{int(time.time())}_{i}.mp4"
                        blob.download_to_filename(local_path)
                        item["file_path"] = local_path
                        log.info(f"Скачано в {local_path}")
                    except Exception as e:
                        log.warning(f"Не удалось скачать {gcs_uri}: {e}")

                out_files.append(item)

            return {"videos": out_files}

        time.sleep(5)

