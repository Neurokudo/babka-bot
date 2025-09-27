# veo_client.py
import os
import time
import tempfile
import pathlib
import json
import logging
import requests
from typing import Optional
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.oauth2 import service_account

log = logging.getLogger("veo_client")

# Конфигурация
PROJECT = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Креды из переменной окружения
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/veo-bot-key.json")
key_text = os.getenv("GCP_KEY_JSON")

if key_text and not os.path.exists(key_path):
    pathlib.Path(key_path).write_text(key_text)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

# Инициализация Vertex AI
try:
    vertexai.init(project=PROJECT, location=LOCATION)
    log.info(f"Vertex AI initialized: project={PROJECT}, location={LOCATION}")
except Exception as e:
    log.error(f"Failed to init Vertex AI: {e}")
    raise

def build_prompt(user_prompt: str, style: Optional[str], replica: Optional[str]) -> str:
    """Создаёт финальный промпт для Veo"""
    parts = []
    
    # Основная сцена
    parts.append(user_prompt.strip())
    
    # Стиль, если указан
    if style:
        parts.append(f"Style: {style}")
    
    # Реплика персонажа, если есть
    if replica:
        parts.append(f'Character says: "{replica}"')
    
    # Технические требования
    parts.append("8 second video, steady camera, clear quality, no text or watermarks in frame")
    
    return ". ".join(p for p in parts if p)

def download_video(url: str, output_path: str) -> None:
    """Скачивает видео по URL"""
    headers = {}
    
    # Если это GCS URL, нужна авторизация
    if url.startswith("gs://") or "storage.googleapis.com" in url:
        # Преобразуем gs:// в https://
        if url.startswith("gs://"):
            bucket_and_path = url[5:]
            url = f"https://storage.googleapis.com/{bucket_and_path}"
        
        # Получаем токен для авторизации
        from google.auth import default
        from google.auth.transport.requests import Request
        
        credentials, _ = default()
        credentials.refresh(Request())
        headers["Authorization"] = f"Bearer {credentials.token}"
    
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def generate_video_sync(user_prompt: str, style: Optional[str], replica: Optional[str], duration_sec: int = 8) -> str:
    """
    Генерирует видео через Veo API
    Возвращает путь к сохранённому mp4 файлу
    """
    try:
        # Создаём модель - используем правильный ID
        model = GenerativeModel("veo-3.0-generate-preview")
        
        # Формируем промпт
        prompt = build_prompt(user_prompt, style, replica)
        log.info(f"Generating video with prompt: {prompt[:100]}...")
        
        # Генерируем контент
        response = model.generate_content(prompt)
        
        # Извлекаем URL видео из ответа
        video_uri = None
        
        # Проходим по кандидатам и ищем file_uri
        for candidate in getattr(response, "candidates", []):
            content = getattr(candidate, "content", None)
            if not content:
                continue
            
            for part in getattr(content, "parts", []):
                file_data = getattr(part, "file_data", None)
                if file_data:
                    video_uri = getattr(file_data, "file_uri", None)
                    if video_uri:
                        break
            
            if video_uri:
                break
        
        if not video_uri:
            # Пытаемся другой способ извлечения
            try:
                resp_dict = response.to_dict()
                log.warning(f"Response structure: {json.dumps(resp_dict, indent=2)[:1000]}")
                
                # Альтернативные пути в структуре ответа
                if "candidates" in resp_dict:
                    for cand in resp_dict["candidates"]:
                        if "content" in cand and "parts" in cand["content"]:
                            for part in cand["content"]["parts"]:
                                if "file_data" in part and "file_uri" in part["file_data"]:
                                    video_uri = part["file_data"]["file_uri"]
                                    break
            except Exception as e:
                log.error(f"Failed to parse response dict: {e}")
        
        if not video_uri:
            raise RuntimeError(f"No video URL in response. Response: {response}")
        
        log.info(f"Got video URI: {video_uri}")
        
        # Создаём временный файл для видео
        tmp_file = tempfile.NamedTemporaryFile(prefix="veo_", suffix=".mp4", delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        # Скачиваем видео
        log.info(f"Downloading video to {tmp_path}")
        download_video(video_uri, tmp_path)
        
        # Проверяем, что файл не пустой
        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            raise RuntimeError("Downloaded video file is empty")
        
        log.info(f"Video saved: {tmp_path} ({file_size} bytes)")
        return tmp_path
        
    except Exception as e:
        log.error(f"Video generation failed: {e}")
        raise RuntimeError(f"Failed to generate video: {str(e)}")
