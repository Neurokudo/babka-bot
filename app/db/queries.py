"""
База данных запросы для Telegram-бота
"""
import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

log = logging.getLogger("db")

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(BigInteger, primary_key=True)  # Исправлено: user_id вместо id
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    coins = Column(Integer, default=0)  # Баланс в монетах
    plan = Column(String(50), default=None)  # План подписки
    plan_expiry = Column(DateTime, nullable=True)  # Дата окончания подписки
    auto_renew = Column(Boolean, default=True)  # Автопродление
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    type = Column(String(50), nullable=False)  # 'purchase', 'spend', 'refund'
    amount = Column(Integer, nullable=False)  # Количество монет
    feature = Column(String(100), nullable=True)  # Какая функция была использована
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def _init_db(self):
        """Инициализация подключения к базе данных"""
        if self._initialized:
            return
            
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # Fallback для локальной разработки
                database_url = "sqlite:///./babka_bot.db"
            
            self.engine = create_engine(database_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Создаем таблицы
            Base.metadata.create_all(bind=self.engine)
            self._initialized = True
            log.info("Database initialized successfully")
        except Exception as e:
            log.warning(f"Database initialization failed: {e}")
            # Создаем заглушку для работы без БД
            self._initialized = False
    
    def get_session(self) -> Session:
        """Получить сессию базы данных"""
        if not self._initialized:
            self._init_db()
        
        if not self._initialized or not self.SessionLocal:
            raise RuntimeError("Database not available")
            
        return self.SessionLocal()
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return None
                
            with self.get_session() as session:
                return session.query(User).filter(User.user_id == user_id).first()
        except Exception as e:
            log.warning(f"Failed to get user {user_id}: {e}")
            return None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None) -> User:
        """Создать нового пользователя"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                # Возвращаем заглушку
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    coins=0
                )
                return user
                
            with self.get_session() as session:
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    coins=0
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
        except Exception as e:
            log.warning(f"Failed to create user {user_id}: {e}")
            # Возвращаем заглушку
            return User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                coins=0
            )
    
    def update_user_balance(self, user_id: int, amount: int) -> bool:
        """Обновить баланс пользователя"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return False
                
            with self.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.coins += amount
                    session.commit()
                    return True
                return False
        except Exception as e:
            log.warning(f"Failed to update balance for user {user_id}: {e}")
            return False
    
    def spend_coins(self, user_id: int, amount: int, feature: str = None) -> bool:
        """Потратить монеты пользователя"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return False
                
            with self.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user and user.coins >= amount:
                    user.coins -= amount
                    session.commit()
                    
                    # Записываем транзакцию
                    transaction = Transaction(
                        user_id=user_id,
                        type='spend',
                        amount=amount,
                        feature=feature
                    )
                    session.add(transaction)
                    session.commit()
                    return True
                return False
        except Exception as e:
            log.warning(f"Failed to spend coins for user {user_id}: {e}")
            return False
    
    def charge_feature(self, user_id: int, feature: str, cost: int, note: str = None) -> bool:
        """Списать монеты за использование функции (алиас для spend_coins)"""
        return self.spend_coins(user_id, cost, feature)
    
    def get_user_balance(self, user_id: int) -> int:
        """Получить баланс пользователя"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return 0
                
            with self.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                return user.coins if user else 0
        except Exception as e:
            log.warning(f"Failed to get balance for user {user_id}: {e}")
            return 0
    
    def add_coins(self, user_id: int, amount: int) -> bool:
        """Добавить монеты пользователю"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return False
                
            with self.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.coins += amount
                    session.commit()
                    
                    # Записываем транзакцию
                    transaction = Transaction(
                        user_id=user_id,
                        type='add',
                        amount=amount,
                        feature='manual_add'
                    )
                    session.add(transaction)
                    session.commit()
                    return True
                return False
        except Exception as e:
            log.warning(f"Failed to add coins for user {user_id}: {e}")
            return False
    
    def add_transaction(self, user_id: int, transaction_type: str, amount: int, 
                       feature: str = None, description: str = None):
        """Добавить запись о транзакции"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return
                
            with self.get_session() as session:
                transaction = Transaction(
                    user_id=user_id,
                    type=transaction_type,
                    amount=amount,
                    feature=feature,
                    description=description
                )
                session.add(transaction)
                session.commit()
        except Exception as e:
            log.warning(f"Failed to add transaction for user {user_id}: {e}")

    def save_user(self, user_id: int, user_data: dict) -> bool:
        """Сохранить данные пользователя"""
        try:
            if not self._initialized:
                self._init_db()
            
            if not self._initialized:
                return False
                
            with self.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    # Обновляем существующего пользователя
                    user.username = user_data.get("username")
                    user.first_name = user_data.get("first_name")
                    user.last_name = user_data.get("last_name")
                    user.coins = user_data.get("coins", 0)
                    user.plan = user_data.get("plan")
                    user.plan_expiry = user_data.get("plan_expiry")
                    user.auto_renew = user_data.get("auto_renew", True)
                    user.is_active = user_data.get("is_active", True)
                else:
                    # Создаем нового пользователя
                    user = User(
                        user_id=user_id,
                        username=user_data.get("username"),
                        first_name=user_data.get("first_name"),
                        last_name=user_data.get("last_name"),
                        coins=user_data.get("coins", 0),
                        plan=user_data.get("plan"),
                        plan_expiry=user_data.get("plan_expiry"),
                        auto_renew=user_data.get("auto_renew", True),
                        is_active=user_data.get("is_active", True)
                    )
                    session.add(user)
                
                session.commit()
                return True
        except Exception as e:
            log.warning(f"Failed to save user {user_id}: {e}")
            return False

# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()
# Не инициализируем БД сразу - это будет сделано при первом обращении

# Функции для совместимости со старым кодом
def init_tables():
    """Инициализация таблиц базы данных"""
    try:
        db_manager._init_db()
        log.info("Database tables initialized successfully")
    except Exception as e:
        log.error(f"Database initialization failed: {e}")
        raise

def get_user(user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    return db_manager.get_user(user_id)

def check_expired_subscriptions():
    """Проверка истекших подписок"""
    try:
        # Пока что заглушка - логика проверки подписок
        log.info("Expired subscriptions check completed")
        return True
    except Exception as e:
        log.warning(f"Failed to check expired subscriptions: {e}")
        return False

def save_user(user_id: int, user_data: dict) -> bool:
    """Сохранить данные пользователя"""
    return db_manager.save_user(user_id, user_data)

def charge_feature(user_id: int, feature: str, cost: int, note: str = None) -> bool:
    """Списать монеты за использование функции (DEPRECATED - используйте db_subscriptions.charge_feature)"""
    # Перенаправляем на новый слой
    from app.db import db_subscriptions as db
    return db.charge_feature(user_id, feature, cost, note)
