#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUN_MIGRATIONS.py - Автоматическое применение миграций при деплое
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 не установлен. Установите: pip install psycopg2-binary")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("migrations")

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migrations():
    """Применяет миграции к базе данных"""
    if not DATABASE_URL:
        log.warning("⚠️ DATABASE_URL не установлен, пропускаем миграции")
        return True
    
    try:
        # Подключаемся к БД
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        
        log.info("🔗 Подключились к базе данных")
        
        # Читаем SQL из файла миграции
        migration_file = Path(__file__).parent / "FINAL_MIGRATION.sql"
        if not migration_file.exists():
            log.error("❌ Файл FINAL_MIGRATION.sql не найден")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Выполняем миграцию
        with conn.cursor() as cursor:
            log.info("🚀 Применяем миграцию...")
            cursor.execute(sql_content)
            log.info("✅ Миграция успешно применена")
        
        conn.close()
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка при применении миграции: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
