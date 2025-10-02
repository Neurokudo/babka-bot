#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИГРАЦИЯ: Добавляет поле admin_coins в существующую таблицу users
"""

import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("migration")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    log.error("DATABASE_URL не установлен!")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    log.info("Подключено к БД. Начинаем миграцию...")
    
    # Проверяем, есть ли уже колонка admin_coins
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='admin_coins'
    """)
    
    if cursor.fetchone():
        log.info("Колонка admin_coins уже существует. Миграция не требуется.")
    else:
        # Добавляем колонку admin_coins
        log.info("Добавляем колонку admin_coins...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN admin_coins INTEGER DEFAULT 0
        """)
        
        # Устанавливаем 500 админских монеток для админа (5015100177)
        log.info("Устанавливаем 500 admin_coins для админа...")
        cursor.execute("""
            UPDATE users 
            SET admin_coins = 500 
            WHERE user_id = 5015100177
        """)
        
        # Обновляем дефолтные бонусы для админа на 2/2/2
        log.info("Обновляем бонусы админа на 2/2/2...")
        cursor.execute("""
            UPDATE users 
            SET video_bonus = 2, photo_bonus = 2, tryon_bonus = 2
            WHERE user_id = 5015100177
        """)
        
        conn.commit()
        log.info("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        
        # Показываем текущее состояние админа
        cursor.execute("""
            SELECT user_id, coins, video_bonus, photo_bonus, tryon_bonus, admin_coins
            FROM users 
            WHERE user_id = 5015100177
        """)
        result = cursor.fetchone()
        if result:
            log.info(f"Текущее состояние админа: user_id={result[0]}, coins={result[1]}, "
                    f"video_bonus={result[2]}, photo_bonus={result[3]}, tryon_bonus={result[4]}, "
                    f"admin_coins={result[5]}")
    
    cursor.close()
    conn.close()
    log.info("Соединение закрыто.")
    
except Exception as e:
    log.error(f"Ошибка миграции: {e}")
    exit(1)

