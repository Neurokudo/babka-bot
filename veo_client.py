# veo_client.py
import os, tempfile, pathlib, json
from typing import Optional
from google.cloud import aiplatform
from google.oauth2 import service_account
from vertexai.preview.generative_models import GenerativeModel

PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

# Достаём креды из переменной окружения (JSON одной строкой в .env)
if creds_json := os.getenv("GOOGLE_CREDENTIALS_JSON"):
    info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(info)
else:
    credentials = None

# Инициализация Vertex AI
aiplatform.init(project=PROJECT, location=LOCATION, credentials=credentials)

_model: Optional[GenerativeModel] = None
def _get_model() -> GenerativeModel:
    global _model
    if _model is None:
        _model = GenerativeModel(MODEL_ID)
    return _model

def build_prompt(user_prompt: str, style: str, replica: Optional[str]) -> str:
    parts = [
        user_prompt.strip(),
        f"Style: {style}" if style else "",
        f'Character line: "{replica}"' if replica else "",
        "Camera: steady, daylight; Clear video, no text/watermarks."
    ]
    return "\n".join(p for p in parts if p)

def generate_video_sync(user_prompt: str, style: str, replica: Optional[str] = None, seconds: int = 8) -> pathlib.Path:
    prompt = build_prompt(user_prompt, style, replica)
    model = _get_model()

    # у GenerativeModel в 1.115.0 метод другой
    op = model.generate(
        prompt=prompt,
        generation_config={"duration": f"{seconds}s"}
    )
    result = op

    video_bytes = getattr(result, "video", None)
    if not video_bytes:
        raise RuntimeError("Veo: не получил данные видео")

    tmp = tempfile.NamedTemporaryFile(prefix="veo_", suffix=".mp4", delete=False)
    tmp.write(video_bytes)
    tmp.flush(); tmp.close()
    return pathlib.Path(tmp.name)
