# -*- coding: utf-8 -*-
"""
app/utils/env.py - Управление переменными окружения
"""

import os
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

# Загружаем .env файл
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class EnvConfig:
    """Конфигурация из переменных окружения"""
    
    # Telegram Bot
    BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # SMTP для репортов
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    FROM_EMAIL: Optional[str] = os.getenv("FROM_EMAIL") or SMTP_USER
    SUPPORT_TO_EMAIL: str = os.getenv("SUPPORT_TO_EMAIL", "antonkudo.ai@gmail.com")
    
    # Admin settings
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "5015100177"))
    ADMIN_CHAT_IDS: List[int] = []
    
    # Payment providers
    YOOKASSA_SHOP_ID: Optional[str] = os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY: Optional[str] = os.getenv("YOOKASSA_SECRET_KEY")
    YOOKASSA_WEBHOOK_SECRET: Optional[str] = os.getenv("YOOKASSA_WEBHOOK_SECRET")
    
    # Bot settings
    ALLOWED_USERS: List[int] = []
    DEFAULT_STYLE: str = os.getenv("DEFAULT_STYLE", "Кино")
    DEFAULT_ORIENTATION: str = os.getenv("DEFAULT_ORIENTATION", "9:16")
    DEFAULT_AUDIO: bool = os.getenv("DEFAULT_AUDIO", "true").lower() == "true"
    
    def __init__(self):
        # Парсим ADMIN_CHAT_IDS
        admin_chat_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
        if admin_chat_raw:
            for piece in admin_chat_raw.split(","):
                piece = piece.strip()
                if piece:
                    try:
                        self.ADMIN_CHAT_IDS.append(int(piece))
                    except ValueError:
                        pass
        
        # Парсим ALLOWED_USERS
        allowed_users_raw = os.getenv("ALLOWED_USERS", "").strip()
        if allowed_users_raw:
            for piece in allowed_users_raw.split(","):
                piece = piece.strip()
                if piece:
                    try:
                        self.ALLOWED_USERS.append(int(piece))
                    except ValueError:
                        pass
        
        # Если ALLOWED_USERS пустой, используем только админа
        if not self.ALLOWED_USERS:
            self.ALLOWED_USERS = [self.ADMIN_ID]
    
    def validate(self) -> List[str]:
        """Проверяет обязательные переменные окружения"""
        errors = []
        
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN не установлен")
        
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY не установлен")
        
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL не установлен")
        
        if not self.SMTP_USER or not self.SMTP_PASS:
            errors.append("SMTP_USER и SMTP_PASS не установлены")
        
        return errors
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом"""
        return user_id == self.ADMIN_ID
    
    def is_allowed_user(self, user_id: int) -> bool:
        """Проверяет, разрешен ли пользователь"""
        return user_id in self.ALLOWED_USERS


# Глобальный экземпляр конфигурации
config = EnvConfig()
