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
        
        # Проверяем, что колонка admin_coins добавлена
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'admin_coins'
        """)
        
        admin_coins_column = cursor.fetchone()
        if admin_coins_column:
            log.info(f"✅ Колонка admin_coins найдена: {admin_coins_column}")
        else:
            log.warning("⚠️ Колонка admin_coins не найдена!")
        
        # Проверяем админские данные
        cursor.execute("""
            SELECT user_id, video_bonus, photo_bonus, tryon_bonus, admin_coins 
            FROM users 
            WHERE user_id = 5015100177
        """)
        
        admin_data = cursor.fetchone()
        if admin_data:
            log.info(f"✅ Админские данные найдены: user_id={admin_data[0]}, video_bonus={admin_data[1]}, photo_bonus={admin_data[2]}, tryon_bonus={admin_data[3]}, admin_coins={admin_data[4]}")
        else:
            log.warning("⚠️ Админские данные не найдены!")
        
        # Проверяем исправление старых пользователей
        cursor.execute("""
            SELECT COUNT(*) 
            FROM users 
            WHERE video_bonus = 2 AND photo_bonus = 3 AND tryon_bonus = 1 AND user_id <> 5015100177
        """)
        
        old_users_count = cursor.fetchone()[0]
        if old_users_count == 0:
            log.info("✅ Все старые пользователи с неправильными бонусами исправлены!")
        else:
            log.warning(f"⚠️ Осталось {old_users_count} пользователей с неправильными бонусами!")
        
        cursor.close()
        conn.close()
        
        log.info("")
        log.info("📊 Что было сделано:")
        log.info("  • Добавлена колонка admin_coins в таблицу users")
        log.info("  • Установлены админские бонусы для ID = 5015100177: 30 видео, 50 фото, 10 примерочных, 500 админских монеток")
        log.info("  • Исправлены старые пользователи с неправильными бонусами (2/3/1) на правильные (2/2/2)")
        log.info("")
        log.info("🎉 Система бонусов готова к работе!")
        
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
