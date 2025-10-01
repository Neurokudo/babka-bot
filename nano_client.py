# nano_client.py
# Экспериментальная «перепостановка» уже одетой модели:
# - изменить позу/ракурс по описанию
# - заменить фон (новая локация)
# Использует Gemini 2.5 Flash Image (preview).

import os, base64, json, logging, requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

log = logging.getLogger("nano-client")

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION   = os.getenv("GCP_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
SCOPES     = ["https://www.googleapis.com/auth/cloud-platform"]
MODEL_ID   = "gemini-2.5-flash-image-preview"

def _load_credentials():
    js = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if js:
        info = json.loads(js)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if path and os.path.exists(path):
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise RuntimeError("No Google credentials (GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS)")

def _access_token() -> str:
    creds = _load_credentials()
    creds.refresh(Request())
    return creds.token

def repose_or_relocate(dressed_bytes: bytes, prompt: str = "", bg_bytes: bytes | None = None) -> bytes:
    """
    Берём уже ОДЕТУЮ модель (результат VTO) и просим Nano Banana слегка изменить позу/сцену.
    Это эксперимент: для стабильной «новой позы» лучше прислать новое фото человека в нужной позе
    и снова вызвать VTO.
    """
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID is not set")

    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:predict"
    )
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json; charset=utf-8"
    }

    inst = []
    inst.append({
        "image": {"bytesBase64Encoded": base64.b64encode(dressed_bytes).decode("utf-8")}
    })
    if bg_bytes:
        inst.append({
            "image": {"bytesBase64Encoded": base64.b64encode(bg_bytes).decode("utf-8")}
        })

    instruction = (
        "Recompose the first image (already dressed person) with minimal identity drift. "
        "Keep the face and body proportions. Adjust pose/background according to the user description. "
        "Avoid text, watermarks and overlays. Output one realistic photo."
    )
    if prompt:
        instruction += " User description: " + prompt.strip()

    body = {
        "instances": inst + [{"prompt": instruction}],
        "parameters": {
            "sampleCount": 1,
            "resolution": "1024x1024"
        }
    }

    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    pred = (data.get("predictions") or [{}])[0]
    b64 = pred.get("bytesBase64Encoded")
    if not b64:
        raise RuntimeError(f"Unexpected nano response: {data}")
    return base64.b64decode(b64)

