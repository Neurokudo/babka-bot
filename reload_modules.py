#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки кэша Python перед запуском бота
"""
import os
import sys
import shutil

def clean_pycache():
    """Удаляет все __pycache__ директории и .pyc файлы"""
    count = 0
    for root, dirs, files in os.walk('.'):
        # Удаляем __pycache__ директории
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Удаляю: {pycache_path}")
            shutil.rmtree(pycache_path)
            count += 1
        
        # Удаляем .pyc файлы
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                print(f"Удаляю: {pyc_path}")
                os.remove(pyc_path)
                count += 1
    
    print(f"\n✅ Удалено {count} файлов/директорий кэша")
    return count

if __name__ == "__main__":
    print("=== Очистка кэша Python ===")
    clean_pycache()
    print("=== Очистка завершена ===")

