import copy
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.billing.coins import atomic_spend_coins, add_coins, get_balance, can_afford
from app.billing.plans import check_subscription, activate_plan, give_welcome_bonus
from app.config.pricing import FEATURE_COSTS

# Стоимость операций в монетах (перенесено из старого конфига)
COST_VIDEO = FEATURE_COSTS["video_8s_audio"]  # 20 монет
COST_TRANSFORM = FEATURE_COSTS["image_basic"]  # 1 монета
COST_TRANSFORM_PREMIUM = FEATURE_COSTS["image_basic"]  # 1 монета (базовое качество)
COST_TRYON = FEATURE_COSTS["virtual_tryon"]  # 3 монеты


class StubCursor:
    def __init__(self, db):
        self.db = db
        self.last_result = []
        self.description = [
            ("user_id", None, None, None, None, None, None),
            ("coins", None, None, None, None, None, None),
            ("plan", None, None, None, None, None, None),
            ("plan_expiry", None, None, None, None, None, None),
            ("admin_coins", None, None, None, None, None, None),
        ]

    def execute(self, query, params=None):
        """Имитирует выполнение SQL запроса"""
        if "SELECT coins FROM users WHERE user_id" in query:
            user_id = params[0] if params else None
            user = self.db.users.get(user_id)
            if user:
                self.last_result = [(user["coins"],)]
            else:
                self.last_result = []
        elif "INSERT INTO users" in query:
            user_id = params[0] if params else None
            coins = params[1] if len(params) > 1 else 0
            self.db.users[user_id] = {
                "user_id": user_id,
                "coins": coins,
                "plan": "lite",
                "plan_expiry": None,
                "admin_coins": 0
            }
        elif "UPDATE users SET coins = coins +" in query:
            amount = params[0] if params else 0
            user_id = params[1] if len(params) > 1 else None
            if user_id in self.db.users:
                self.db.users[user_id]["coins"] += amount
        elif "INSERT INTO transactions" in query and "operation_type" in query:
            user_id = params[0] if params else None
            operation_type = params[1] if len(params) > 1 else ""
            coins_spent = params[2] if len(params) > 2 else 0
            transaction_id = self.db.next_transaction_id
            self.db.next_transaction_id += 1
            self.db.transactions.append({
                "id": transaction_id,
                "user_id": user_id,
                "operation_type": operation_type,
                "coins_spent": coins_spent,
                "status": "completed"
            })
            self.last_result = [(transaction_id,)]
        elif "UPDATE users SET coins = coins -" in query:
            amount = params[0] if params else 0
            user_id = params[1] if len(params) > 1 else None
            if user_id in self.db.users:
                self.db.users[user_id]["coins"] -= amount
        elif "INSERT INTO transactions" in query:
            user_id = params[0] if params else None
            operation_type = params[1] if len(params) > 1 else ""
            coins_spent = params[2] if len(params) > 2 else 0
            transaction_id = self.db.next_transaction_id
            self.db.next_transaction_id += 1
            self.db.transactions.append({
                "id": transaction_id,
                "user_id": user_id,
                "operation_type": operation_type,
                "coins_spent": coins_spent,
                "status": "pending"
            })
            self.last_result = [(transaction_id,)]
        elif "SELECT COUNT(*) FROM transactions WHERE user_id" in query:
            user_id = params[0] if params else None
            count = len([tx for tx in self.db.transactions if tx["user_id"] == user_id and tx["operation_type"] == "welcome_bonus"])
            self.last_result = [(count,)]
        elif "SELECT * FROM users WHERE user_id" in query:
            user_id = params[0] if params else None
            user = self.db.users.get(user_id)
            if user:
                self.last_result = [(user["user_id"], user["coins"], user["plan"], user["plan_expiry"], user["admin_coins"])]
            else:
                self.last_result = []
        elif "UPDATE users SET plan" in query:
            # Обновление плана
            pass
        elif "UPDATE users SET admin_coins" in query:
            # Обновление админских монет
            pass
        else:
            self.last_result = []

    def fetchone(self):
        """Возвращает одну строку результата"""
        if self.last_result:
            return self.last_result[0]
        return None

    def commit(self):
        """Имитирует коммит транзакции"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class StubDB:
    def __init__(self):
        self.users = {}
        self.transactions = []
        self.payments = []
        self.next_transaction_id = 1
        self.connection = self  # Для совместимости с реальным DB

    def cursor(self):
        """Возвращает контекстный менеджер для cursor"""
        return StubCursor(self)

    def commit(self):
        """Имитирует коммит транзакции"""
        pass

    def get_user(self, user_id):
        return copy.deepcopy(self.users.get(user_id))

    def save_user(self, user_id, user_data):
        self.users[user_id] = copy.deepcopy(user_data)

    def atomic_spend_coins(self, user_id, cost, operation_type):
        """Имитирует атомарное списание монет"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        if user["coins"] < cost:
            return None
        
        user["coins"] -= cost
        transaction_id = self.next_transaction_id
        self.next_transaction_id += 1
        
        self.transactions.append({
            "id": transaction_id,
            "user_id": user_id,
            "operation_type": operation_type,
            "coins_spent": cost,
            "status": "pending"
        })
        
        return transaction_id

    def update_transaction_status(self, transaction_id, status):
        """Обновляет статус транзакции"""
        for tx in self.transactions:
            if tx["id"] == transaction_id:
                tx["status"] = status
                break

    def add_refund_transaction(self, user_id, amount, original_transaction_id=None):
        """Добавляет транзакцию возврата"""
        user = self.users.get(user_id)
        if user:
            user["coins"] += amount
        
        transaction_id = self.next_transaction_id
        self.next_transaction_id += 1
        
        self.transactions.append({
            "id": transaction_id,
            "user_id": user_id,
            "operation_type": f"refund{'_' + str(original_transaction_id) if original_transaction_id else ''}",
            "coins_spent": amount,
            "status": "refunded"
        })
        
        return transaction_id


@pytest.fixture
def stub_db(monkeypatch):
    stub = StubDB()
    # Мокаем глобальную переменную db
    import app.db.queries
    monkeypatch.setattr(app.db.queries, "db", stub)
    
    # Мокаем connection для прямого использования в функциях
    import app.billing.coins
    monkeypatch.setattr(app.billing.coins, "db", stub)
    
    import app.billing.plans
    monkeypatch.setattr(app.billing.plans, "db", stub)
    
    return stub


def make_user(coins=100):
    return {
        "user_id": 1,
        "coins": coins,
        "plan": "lite",
        "plan_expiry": None,
        "admin_coins": 0,
    }


def test_video_generation_charges_20_coins(stub_db):
    """Тест: генерация видео списывает 20 монет"""
    user = make_user(coins=30)
    stub_db.users[1] = user

    transaction_id = atomic_spend_coins(1, COST_VIDEO, "video")
    
    assert transaction_id is not None
    assert user["coins"] == 10  # 30 - 20
    assert stub_db.transactions[-1]["coins_spent"] == COST_VIDEO
    assert stub_db.transactions[-1]["operation_type"] == "video"


def test_photo_basic_and_premium_costs(stub_db):
    """Тест: фото базовое и премиум имеют одинаковую стоимость (1 монета)"""
    user = make_user(coins=10)
    stub_db.users[1] = user

    # Базовое фото
    tx1 = atomic_spend_coins(1, COST_TRANSFORM, "photo")
    assert tx1 is not None
    assert user["coins"] == 9  # 10 - 1
    assert stub_db.transactions[-1]["coins_spent"] == COST_TRANSFORM

    # Премиум фото (та же стоимость)
    tx2 = atomic_spend_coins(1, COST_TRANSFORM_PREMIUM, "photo_premium")
    assert tx2 is not None
    assert user["coins"] == 8  # 9 - 1
    assert stub_db.transactions[-1]["coins_spent"] == COST_TRANSFORM_PREMIUM


def test_tryon_costs_three_coins(stub_db):
    """Тест: примерочная стоит 3 монеты"""
    user = make_user(coins=5)
    stub_db.users[1] = user

    transaction_id = atomic_spend_coins(1, COST_TRYON, "tryon")
    
    assert transaction_id is not None
    assert user["coins"] == 2  # 5 - 3
    assert stub_db.transactions[-1]["coins_spent"] == COST_TRYON


def test_insufficient_funds_returns_none(stub_db):
    """Тест: недостаточно средств возвращает None"""
    user = make_user(coins=5)
    stub_db.users[1] = user

    transaction_id = atomic_spend_coins(1, COST_VIDEO, "video")  # 20 монет
    
    assert transaction_id is None
    assert user["coins"] == 5  # не изменился


def test_add_coins_increases_balance(stub_db):
    """Тест: добавление монет увеличивает баланс"""
    user = make_user(coins=10)
    stub_db.users[1] = user

    new_balance = add_coins(1, 50, "test")
    
    assert new_balance == 60
    assert user["coins"] == 60


def test_can_afford_checks_balance(stub_db):
    """Тест: проверка достаточности средств"""
    user = make_user(coins=15)
    stub_db.users[1] = user

    assert can_afford(1, 10) is True
    assert can_afford(1, 20) is False


def test_activate_plan_adds_coins_and_sets_expiry(stub_db):
    """Тест: активация плана начисляет монеты и устанавливает срок"""
    user = make_user(coins=0)
    stub_db.users[1] = user

    result = activate_plan(1, "lite")
    assert result["coins"] == 120  # план lite дает 120 монет
    assert result["plan"] == "lite"
    assert result["plan_expiry"] is None

    result = activate_plan(1, "standard")
    assert result["plan"] == "standard"
    assert result["coins"] == 330  # 120 + 210
    assert result["plan_expiry"] is not None


def test_check_subscription_resets_expired_plan(stub_db):
    """Тест: проверка подписки сбрасывает истекший план"""
    from datetime import datetime, timedelta, timezone
    
    expired_user = {
        "user_id": 2,
        "coins": 50,
        "plan": "standard",
        "plan_expiry": datetime.now(timezone.utc) - timedelta(days=1),
        "admin_coins": 0,
    }
    stub_db.users[2] = expired_user

    updated = check_subscription(2)
    assert updated["plan"] == "lite"
    assert updated["plan_expiry"] is None


def test_give_welcome_bonus_once(stub_db):
    """Тест: стартовые бонусы выдаются только один раз"""
    user = make_user(coins=0)
    stub_db.users[1] = user

    # Первый раз - выдаем бонусы
    result1 = give_welcome_bonus(1)
    assert result1 is True
    assert user["coins"] == 23  # стартовые бонусы

    # Второй раз - не выдаем
    result2 = give_welcome_bonus(1)
    assert result2 is False
    assert user["coins"] == 23  # не изменился


def test_transaction_logging(stub_db):
    """Тест: все операции логируются в транзакции"""
    user = make_user(coins=20)
    stub_db.users[1] = user

    # Списание
    tx1 = atomic_spend_coins(1, 5, "test_operation")
    assert tx1 is not None
    assert len(stub_db.transactions) == 1
    assert stub_db.transactions[0]["operation_type"] == "test_operation"
    assert stub_db.transactions[0]["coins_spent"] == 5

    # Добавление
    add_coins(1, 10, "test_add")
    # Добавление монет теперь тоже создает транзакцию
    assert len(stub_db.transactions) == 2