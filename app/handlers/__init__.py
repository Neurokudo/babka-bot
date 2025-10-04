# app/handlers/__init__.py
"""Обработчики для бота"""

from .router import router, register_router, HANDLERS

__all__ = ['router', 'register_router', 'HANDLERS']
