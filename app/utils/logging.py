"""
Настройка логирования для Telegram-бота
"""
import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Настройка логирования для приложения
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для записи логов (опционально)
    
    Returns:
        Настроенный логгер
    """
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Создаем логгер
    logger = logging.getLogger("babka_bot")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для файла (если указан)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с указанным именем
    
    Args:
        name: Имя логгера
    
    Returns:
        Логгер
    """
    return logging.getLogger(name)
