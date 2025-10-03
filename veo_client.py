import os
import time
import json
import base64
import logging
import requests
import subprocess
from google.auth.transport.requests import Request
from google.oauth2 import service_account

log = logging.getLogger("veo_client")
logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ornate-producer-473220-g2")
LOCATION   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL      = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")
OUTPUT_GCS_URI = os.getenv("VEO_OUTPUT_GCS_URI")  # gs://bucket/path/
DOWNLOAD = os.getenv("DOWNLOAD_VIDEOS", "1") == "1"
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))

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


def _post_with_retry(session, url: str, payload: dict, timeout: int = HTTP_TIMEOUT,
                     attempts: int = HTTP_RETRIES):
    """Отправляет POST с повторными попытками и ограничением по тайм-ауту."""
    backoff = 2
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = session.post(url, json=payload, timeout=timeout)
            if response.status_code < 400:
                return response

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = RuntimeError(
                    f"Retryable error {response.status_code}: {response.text[:256]}"
                )
            else:
                response.raise_for_status()
        except requests.RequestException as exc:
            last_error = exc

        if attempt < attempts:
            sleep_for = backoff ** (attempt - 1)
            log.warning("Veo request retry %s/%s after error: %s", attempt, attempts, last_error)
            time.sleep(min(15, sleep_for))

    raise RuntimeError(f"Veo request failed after {attempts} attempts: {last_error}")

def _fix_aspect_with_ffmpeg(input_path: str, aspect="9:16") -> str:
    """Прогон через ffmpeg, чтобы Telegram не сплющивал превью."""
    fixed_path = input_path.replace(".mp4", "_fixed.mp4")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-aspect", aspect,
            "-movflags", "+faststart",
            fixed_path
        ], check=True)
        return fixed_path
    except Exception as e:
        log.warning(f"FFmpeg fix failed: {e}")
        return input_path

def generate_video_sync(prompt: str, duration: int = 8, aspect_ratio: str = "9:16", with_audio: bool = True):
    sess = _authorized_session()
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL}:predictLongRunning"
    )

    params = {
        "sampleCount": 1,
        "resolution": "720p",  # Veo 3 поддерживает только 720p или 1080p
        "duration": f"{duration}s",
        "aspectRatio": aspect_ratio,
        "generateAudio": with_audio,  # Управляем генерацией аудио
    }
    if OUTPUT_GCS_URI:
        params["storageUri"] = OUTPUT_GCS_URI

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": params,
    }

    log.info(f"Запрос генерации: {url}")
    r = _post_with_retry(sess, url, body)

    resp = r.json()
    op_name = resp.get("name")
    if not op_name:
        raise RuntimeError(f"Не удалось получить operation name: {resp}")
    log.info(f"Получили op_name: {op_name}")

    return _poll_and_collect(sess, op_name)

def _poll_and_collect(sess, op_name: str):
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL}:fetchPredictOperation"
    )
    payload = {"operationName": op_name}

    while True:
        rr = _post_with_retry(sess, url, payload, timeout=HTTP_TIMEOUT, attempts=HTTP_RETRIES)

        data = rr.json()
        if data.get("done"):
            videos = (data.get("response") or {}).get("videos") or []
            out_files = []
            if not videos:
                return {"videos": []}

            from google.cloud import storage
            storage_client = storage.Client(project=PROJECT_ID, credentials=_get_credentials())
            ts = int(time.time())

            for i, v in enumerate(videos):
                item = {}
                gcs_uri = v.get("gcsUri")
                if gcs_uri:
                    _, path = gcs_uri.split("gs://", 1)
                    bucket_name, blob_name = path.split("/", 1)
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    local_path = f"video_{ts}_{i}.mp4"
                    blob.download_to_filename(local_path)
                    log.info(f"Скачано в {local_path}")
                    fixed_path = _fix_aspect_with_ffmpeg(local_path)
                    item["uri"] = gcs_uri
                    item["file_path"] = fixed_path
                    out_files.append(item)
                    continue

                b64 = v.get("bytesBase64Encoded")
                if b64:
                    raw = base64.b64decode(b64)
                    local_path = f"video_{ts}_{i}.mp4"
                    with open(local_path, "wb") as f:
                        f.write(raw)
                    fixed_path = _fix_aspect_with_ffmpeg(local_path)
                    item["file_path"] = fixed_path
                    out_files.append(item)
                    continue

            return {"videos": out_files}
        time.sleep(5)
