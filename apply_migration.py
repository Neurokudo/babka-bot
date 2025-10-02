#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для применения миграции FINAL_MIGRATION.sql к Railway БД
Использование: python apply_migration.py "postgres://user:password@host:port/database"
"""

import sys
import os
import psycopg2
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def apply_migration(database_url):
    """Применяет миграцию к базе данных"""
    
    migration_file = "FINAL_MIGRATION.sql"
    
    # Проверяем существование файла миграции
    if not os.path.exists(migration_file):
        log.error(f"Файл миграции {migration_file} не найден!")
        return False
    
    try:
        # Читаем содержимое миграции
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        log.info("🚀 Подключаемся к Railway БД...")
        
        # Подключаемся к базе данных
        conn = psycopg2.connect(database_url)
        conn.autocommit = True  # Включаем автокоммит для транзакций
        
        cursor = conn.cursor()
        
        log.info("⏳ Применяем миграцию...")
        
        # Выполняем миграцию
        cursor.execute(migration_sql)
        
        log.info("✅ Миграция успешно применена!")
        
        # Проверяем результат
        log.info("🔍 Проверяем результат миграции...")
        
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
              AND column_name IN ('coins', 'admin_coins', 'plan', 'plan_expiry')
        """)
        present_columns = {row[0] for row in cursor.fetchall()}
        missing = {"coins", "admin_coins", "plan", "plan_expiry"} - present_columns
        if missing:
            log.warning("⚠️ Не найдены колонки: %s", ", ".join(sorted(missing)))
        else:
            log.info("✅ Все нужные колонки (coins, admin_coins, plan, plan_expiry) на месте")

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
              AND column_name IN ('video_bonus', 'photo_bonus', 'tryon_bonus', 'videos_allowed', 'photos_allowed')
        """)
        legacy = [row[0] for row in cursor.fetchall()]
        if legacy:
            log.warning("⚠️ Устаревшие колонки не удалены: %s", ", ".join(legacy))
        else:
            log.info("✅ Устаревшие бонусные колонки удалены")

        cursor.execute("""
            SELECT user_id, coins, admin_coins, plan, plan_expiry
            FROM users
            WHERE user_id = 5015100177
        """)
        admin_row = cursor.fetchone()
        if admin_row:
            log.info(
                "✅ Админская запись: id=%s, coins=%s, admin_coins=%s, plan=%s, plan_expiry=%s",
                *admin_row
            )
        else:
            log.warning("⚠️ Админская запись с ID 5015100177 не найдена")
        
        cursor.close()
        conn.close()
        
        log.info("")
        log.info("📊 Что сделала миграция:")
        log.info("  • Обновила таблицу users под монетную систему (coins, plan, plan_expiry, admin_coins)")
        log.info("  • Очистила старые бонусные поля и добавила processed_payments")
        log.info("  • Привела transactions к унифицированному виду (before/after/delta/metadata)")
        log.info("")
        log.info("🎉 Монетная система готова. Можно деплоить! 🚀")
        
        return True
        
    except psycopg2.Error as e:
        log.error(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        log.error(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    """Основная функция"""
    
    if len(sys.argv) != 2:
        print("❌ Ошибка: Не указана строка подключения к БД")
        print("")
        print("Использование:")
        print(f"  {sys.argv[0]} \"postgres://user:password@host:port/database\"")
        print("")
        print("Пример:")
        print(f"  {sys.argv[0]} \"postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway\"")
        print("")
        print("Получить строку подключения можно в Railway:")
        print("1. Перейдите в ваш проект на Railway")
        print("2. Выберите PostgreSQL базу данных")
        print("3. Перейдите в раздел 'Variables'")
        print("4. Скопируйте значение DATABASE_URL")
        sys.exit(1)
    
    database_url = sys.argv[1]
    
    # Скрываем пароль в логах
    safe_url = database_url.split('@')[0] + '@***' if '@' in database_url else '***'
    log.info(f"🔗 База данных: {safe_url}")
    
    if apply_migration(database_url):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
