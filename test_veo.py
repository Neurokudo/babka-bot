import os, pathlib, json
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# --- Креды ---
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/veo-bot-key.json")
key_text = os.getenv("GCP_KEY_JSON")
if key_text:
    pathlib.Path(key_path).write_text(key_text)

project_id = os.getenv("GCP_PROJECT_ID")
vertexai.init(project=project_id, location="us-central1")

print("Ping Veo…")
try:
    # ВАЖНО: корректный ID модели
from vertexai.generative_models import GenerativeModel
model = GenerativeModel("veo-3.0-fast")

    # Без нестабильных полей — дефолты модели
    resp = model.generate_content("dancing robot")

    # --- Достаём URL видео ---
    uri = None
    try:
        for c in getattr(resp, "candidates", []) or []:
            cont = getattr(c, "content", None)
            if not cont:
                continue
            for p in getattr(cont, "parts", []) or []:
                fd = getattr(p, "file_data", None)
                if fd and getattr(fd, "file_uri", None):
                    uri = fd.file_uri
                    break
            if uri:
                break
    except Exception:
        pass

    if not uri:
        try:
            print("⚠️ RAW response:", json.dumps(resp.to_dict(), ensure_ascii=False)[:2000], "…")
        except Exception:
            print("⚠️ RAW response (repr):", repr(resp))

    print("✅ URL:" if uri else "❌ URL not found", uri if uri else "")
except Exception as e:
    print("❌ Veo error:", e)
