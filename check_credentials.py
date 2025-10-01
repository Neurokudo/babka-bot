#!/usr/bin/env python3
"""
Скрипт для проверки настроек Google Cloud credentials
"""

import os
import sys
import json
import base64
from dotenv import load_dotenv
from pathlib import Path

# Загружаем .env файл
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def check_credentials():
    """Проверяет доступность Google Cloud credentials"""
    print("🔍 Проверка Google Cloud credentials...")
    
    # Проверяем переменные окружения
    env_vars = [
        "GCP_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT",
        "GCP_LOCATION",
        "GOOGLE_CLOUD_LOCATION", 
        "GCP_KEY_JSON_B64",
        "GOOGLE_CREDENTIALS_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]
    
    print("\n📋 Переменные окружения:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if "JSON" in var or "B64" in var:
                print(f"✅ {var}: установлена (длина: {len(value)} символов)")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: не установлена")
    
    # Проверяем GCP_KEY_JSON_B64
    print("\n🔑 Проверка GCP_KEY_JSON_B64:")
    key_b64 = os.getenv("GCP_KEY_JSON_B64")
    if key_b64:
        try:
            key_json = base64.b64decode(key_b64).decode("utf-8")
            key_data = json.loads(key_json)
            print(f"✅ JSON декодирован успешно")
            print(f"   Project ID: {key_data.get('project_id', 'не найден')}")
            print(f"   Client Email: {key_data.get('client_email', 'не найден')}")
            print(f"   Private Key ID: {key_data.get('private_key_id', 'не найден')[:20]}...")
        except Exception as e:
            print(f"❌ Ошибка декодирования: {e}")
    else:
        print("❌ GCP_KEY_JSON_B64 не установлена")
    
    # Проверяем GOOGLE_CREDENTIALS_JSON
    print("\n🔑 Проверка GOOGLE_CREDENTIALS_JSON:")
    json_str = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if json_str:
        try:
            json_data = json.loads(json_str)
            print(f"✅ JSON парсится успешно")
            print(f"   Project ID: {json_data.get('project_id', 'не найден')}")
            print(f"   Client Email: {json_data.get('client_email', 'не найден')}")
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
    else:
        print("❌ GOOGLE_CREDENTIALS_JSON не установлена")
    
    # Проверяем файл credentials
    print("\n📁 Проверка GOOGLE_APPLICATION_CREDENTIALS:")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if creds_path:
        if os.path.exists(creds_path):
            print(f"✅ Файл существует: {creds_path}")
            try:
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                print(f"   Project ID: {creds_data.get('project_id', 'не найден')}")
                print(f"   Client Email: {creds_data.get('client_email', 'не найден')}")
            except Exception as e:
                print(f"❌ Ошибка чтения файла: {e}")
        else:
            print(f"❌ Файл не найден: {creds_path}")
    else:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS не установлена")
    
    print("\n💡 Рекомендации:")
    print("1. Убедитесь, что хотя бы один из способов credentials настроен")
    print("2. Проверьте, что сервисный аккаунт имеет права на Vertex AI")
    print("3. Убедитесь, что ключ не истек и не поврежден")
    print("4. Для production используйте GCP_KEY_JSON_B64 (base64 encoded)")

if __name__ == "__main__":
    check_credentials()
