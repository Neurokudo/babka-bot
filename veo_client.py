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

# ---- Конфиг ----
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ornate-producer-473220-g2")
LOCATION   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL      = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

# Если хочешь принудительно писать выход в GCS — укажи путь вида gs://bucket/path/
# Тогда ответ вернёт gcsUri. Если не указать, Veo может вернуть base64.
OUTPUT_GCS_URI = os.getenv("VEO_OUTPUT_GCS_URI")  # например: "gs://my-bucket/veo-out/"

# По умолчанию — СКАЧИВАЕМ из GCS локально и отдаём файл в ТГ
DOWNLOAD = os.getenv("DOWNLOAD_VIDEOS", "1") == "1"

# ---- Service Account ----
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
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {creds.token}"})
    return s

# ---- Основная генерация ----
def generate_video_sync(
    prompt: str,
    duration: int = 8,
    aspect_ratio: str = "9:16",
    resolution: str = "720p",
    sample_count: int = 1,
    generate_audio: bool = True,
):
    """
    Синхронная генерация видео через Veo 3 Fast (через long-running operation).
    Возвращает: {"videos": [{"uri": "gs://...", "file_path": "/path/to.mp4"} ...]}
    """
    sess = _authorized_session()
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL}:predictLongRunning"
    )

    params = {
        "sampleCount": max(1, min(2, int(sample_count))),
        "resolution": resolution,
        "duration": f"{duration}s",
        "aspectRatio": aspect_ratio,
        "generateAudio": bool(generate_audio),
    }
    if OUTPUT_GCS_URI:
        params["storageUri"] = OUTPUT_GCS_URI

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": params,
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

    return _poll_and_collect(sess, op_name)

def _poll_and_collect(sess, op_name: str):
    """
    Опрос состояния через fetchPredictOperation и сбор mp4:
    - если вернулся gcsUri — пытаемся скачать через google-cloud-storage;
    - если вернулись base64-байты — пишем локальный mp4.
    """
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL}:fetchPredictOperation"
    )
    payload = {"operationName": op_name}  # ВАЖНО: именно operationName

    log.info(f"Poll через fetchPredictOperation: {url} | payload={payload}")

    while True:
        rr = sess.post(url, json=payload)
        if rr.status_code != 200:
            raise RuntimeError(f"Poll error {rr.status_code}: {rr.text}")

        data = rr.json()

        # Ошибка операции
        if "error" in data:
            code = data["error"].get("code")
            msg  = data["error"].get("message")
            raise RuntimeError(f"Veo operation error {code}: {msg}")

        if data.get("done"):
            log.info("Операция завершена")
            videos = (data.get("response") or {}).get("videos") or []
            out_files = []

            if not videos:
                return {"videos": []}

            # Для скачивания из GCS нам нужен storage-клиент
            storage_client = None
            if DOWNLOAD:
                try:
                    from google.cloud import storage
                    storage_client = storage.Client(
                        project=PROJECT_ID,
                        credentials=_get_credentials()
                    )
                except Exception as e:
                    log.warning(f"Не удалось инициализировать google-cloud-storage: {e}")
                    storage_client = None

            ts = int(time.time())
            for i, v in enumerate(videos):
                item = {}
                # Вариант 1: ссылка на GCS
                gcs_uri = v.get("gcsUri")
                if gcs_uri:
                    item["uri"] = gcs_uri

                    if DOWNLOAD and storage_client:
                        try:
                            assert gcs_uri.startswith("gs://")
                            _, path = gcs_uri.split("gs://", 1)
                            bucket_name, blob_name = path.split("/", 1)

                            bucket = storage_client.bucket(bucket_name)
                            blob   = bucket.blob(blob_name)

                            local_path = f"video_{ts}_{i}.mp4"
                            blob.download_to_filename(local_path)
                            item["file_path"] = local_path
                            log.info(f"Скачано из GCS в {local_path}")
                        except Exception as e:
                            log.warning(f"Не удалось скачать {gcs_uri}: {e}")

                    out_files.append(item)
                    continue

                # Вариант 2: base64 в ответе
                b64 = v.get("bytesBase64Encoded")
                if b64:
                    try:
                        raw = base64.b64decode(b64)
                        local_path = f"video_{ts}_{i}.mp4"
                        with open(local_path, "wb") as f:
                            f.write(raw)
                        item["file_path"] = local_path
                        log.info(f"Видеобайт-ответ сохранён в {local_path}")
                    except Exception as e:
                        log.warning(f"Не удалось сохранить base64 видео: {e}")
                    out_files.append(item)
                    continue

                # Если ни gcsUri, ни base64 — просто пробрасываем что есть
                out_files.append(v)

            return {"videos": out_files}

        time.sleep(5)

