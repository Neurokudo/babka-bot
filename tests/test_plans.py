import copy
from datetime import datetime, timedelta, timezone

import pytest

from app.billing.plans import activate_plan, check_subscription, get_user_plan_info
from app.billing.config import PLANS


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
    def __init__(self, initial_user=None):
        self.users = {}
        if initial_user:
            self.users[initial_user["user_id"]] = initial_user
        self.saved = []
        self.transactions = []
        self.next_transaction_id = 1
        self.connection = self  # Для совместимости с реальным DB

    def get_user(self, user_id):
        if user_id in self.users:
            return copy.deepcopy(self.users[user_id])
        return None

    def save_user(self, user_id, data):
        self.users[user_id] = copy.deepcopy(data)
        self.saved.append(copy.deepcopy(data))

    def cursor(self):
        """Возвращает контекстный менеджер для cursor"""
        return StubCursor(self)

    def commit(self):
        """Имитирует коммит транзакции"""
        pass

    def atomic_spend_coins(self, user_id, cost, operation_type):
        # Имитируем списание монет
        if user_id in self.users:
            self.users[user_id]["coins"] -= cost
        transaction_id = len(self.transactions) + 1
        self.transactions.append({
            "id": transaction_id,
            "user_id": user_id,
            "operation_type": operation_type,
            "coins_spent": cost,
            "status": "pending"
        })
        return transaction_id

    def update_transaction_status(self, transaction_id, status):
        for tx in self.transactions:
            if tx["id"] == transaction_id:
                tx["status"] = status
                break

    def add_refund_transaction(self, user_id, amount, original_transaction_id=None):
        if user_id in self.users:
            self.users[user_id]["coins"] += amount
        transaction_id = len(self.transactions) + 1
        self.transactions.append({
            "id": transaction_id,
            "user_id": user_id,
            "operation_type": f"refund{'_' + str(original_transaction_id) if original_transaction_id else ''}",
            "coins_spent": amount,
            "status": "refunded"
        })
        return transaction_id


@pytest.fixture
def stub_db(monkeypatch, initial_user=None):
    stub = StubDB(initial_user)
    import app.db.queries
    monkeypatch.setattr(app.db.queries, "db", stub)
    
    # Мокаем connection для прямого использования в функциях
    import app.billing.coins
    monkeypatch.setattr(app.billing.coins, "db", stub)
    
    import app.billing.plans
    monkeypatch.setattr(app.billing.plans, "db", stub)
    
    return stub


def test_activate_plan_adds_coins_and_sets_expiry(stub_db):
    """Тест: активация плана начисляет монеты и устанавливает срок"""
    user = {
        "user_id": 1,
        "coins": 0,
        "plan": "lite",
        "plan_expiry": None,
        "admin_coins": 0,
    }
    stub_db.users[1] = user

    result = activate_plan(1, "lite")
    assert result["coins"] == PLANS["lite"]["coins"]
    assert result["plan"] == "lite"
    assert result["plan_expiry"] is None

    result = activate_plan(1, "standard")
    assert result["plan"] == "standard"
    assert result["coins"] == PLANS["lite"]["coins"] + PLANS["standard"]["coins"]
    expiry = result["plan_expiry"]
    assert isinstance(expiry, datetime)
    if expiry.tzinfo:
        now_ref = datetime.now(timezone.utc)
    else:
        now_ref = datetime.now(timezone.utc).replace(tzinfo=None)
    diff_days = (expiry - now_ref).days
    assert 28 <= diff_days <= 31


def test_check_subscription_resets_expired_plan(stub_db):
    """Тест: проверка подписки сбрасывает истекший план"""
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


def test_get_user_plan_info(stub_db):
    """Тест: получение информации о плане пользователя"""
    user = {
        "user_id": 3,
        "coins": 100,
        "plan": "standard",
        "plan_expiry": datetime.now(timezone.utc) + timedelta(days=15),
        "admin_coins": 0,
    }
    stub_db.users[3] = user

    plan_info = get_user_plan_info(3)
    assert plan_info["plan"] == "standard"
    assert plan_info["is_active"] is True
    assert plan_info["plan_info"]["name"] == "Стандарт"


def test_plan_expiry_text(stub_db):
    """Тест: текстовое описание срока действия плана"""
    from app.billing.plans import get_plan_expiry_text
    
    # Активный план
    active_user = {
        "user_id": 4,
        "coins": 50,
        "plan": "pro",
        "plan_expiry": datetime.now(timezone.utc) + timedelta(days=10),
        "admin_coins": 0,
    }
    stub_db.users[4] = active_user
    
    expiry_text = get_plan_expiry_text(4)
    assert "Осталось" in expiry_text
    assert "9" in expiry_text or "10" in expiry_text  # может быть 9 или 10 дней
    
    # Истекший план
    expired_user = {
        "user_id": 5,
        "coins": 30,
        "plan": "standard",
        "plan_expiry": datetime.now(timezone.utc) - timedelta(days=1),
        "admin_coins": 0,
    }
    stub_db.users[5] = expired_user
    
    expiry_text = get_plan_expiry_text(5)
    assert expiry_text == "Бесплатный план"  # истекший план сбрасывается на lite
    
    # Lite план
    lite_user = {
        "user_id": 6,
        "coins": 20,
        "plan": "lite",
        "plan_expiry": None,
        "admin_coins": 0,
    }
    stub_db.users[6] = lite_user
    
    expiry_text = get_plan_expiry_text(6)
    assert expiry_text == "Бесплатный план"


def test_welcome_bonus_given_once(stub_db):
    """Тест: стартовые бонусы выдаются только один раз"""
    from app.billing.plans import give_welcome_bonus
    
    user = {
        "user_id": 7,
        "coins": 0,
        "plan": "lite",
        "plan_expiry": None,
        "admin_coins": 0,
    }
    stub_db.users[7] = user
    
    # Первый раз - выдаем бонусы
    result1 = give_welcome_bonus(7)
    assert result1 is True
    assert stub_db.users[7]["coins"] == 23  # стартовые бонусы
    
    # Второй раз - не выдаем
    result2 = give_welcome_bonus(7)
    assert result2 is False
    assert stub_db.users[7]["coins"] == 23  # не изменился


def test_plan_extension(stub_db):
    """Тест: продление существующей подписки"""
    from datetime import datetime, timedelta, timezone
    
    # Пользователь с активной подпиской
    user = {
        "user_id": 8,
        "coins": 100,
        "plan": "standard",
        "plan_expiry": datetime.now(timezone.utc) + timedelta(days=10),
        "admin_coins": 0,
    }
    stub_db.users[8] = user
    
    original_expiry = user["plan_expiry"]
    result = activate_plan(8, "standard")
    
    # План должен быть продлен на 30 дней
    assert result["plan"] == "standard"
    assert result["plan_expiry"] > original_expiry
    assert result["coins"] == 100 + PLANS["standard"]["coins"]  # старые + новые монеты