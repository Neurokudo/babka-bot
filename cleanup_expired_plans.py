#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматической проверки и сброса истекших тарифов
Запускается по cron или вручную
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from database import db
from subscription_system import check_and_reset_expired_plans

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("subscription_cleanup")

def main():
    """Основная функция для проверки истекших тарифов"""
    try:
        log.info("Starting subscription cleanup...")
        
        # Проверяем подключение к БД
        if not db.connection:
            log.error("Database connection not available")
            return False
        
        # Проверяем и сбрасываем истекшие тарифы
        expired_users = check_and_reset_expired_plans()
        
        if expired_users:
            log.info(f"Reset expired plans for {len(expired_users)} users: {expired_users}")
        else:
            log.info("No expired plans found")
        
        log.info("Subscription cleanup completed successfully")
        return True
        
    except Exception as e:
        log.error(f"Error during subscription cleanup: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
