import copy
from datetime import datetime, timedelta, timezone

import pytest

import billing


class StubDB:
    def __init__(self, initial_user=None):
        self.user = initial_user or {
            "user_id": 1,
            "coins": 0,
            "plan": "lite",
            "plan_expiry": None,
            "admin_coins": 0,
        }
        self.saved = []
        self.activated = []
        self.reset_calls = []
        self.topups = []

    def get_user(self, user_id):
        if self.user and self.user.get("user_id") == user_id:
            return copy.deepcopy(self.user)
        return None

    def save_user(self, user_id, data):
        self.user = copy.deepcopy(data)
        self.user["user_id"] = user_id
        self.saved.append(copy.deepcopy(self.user))

    def activate_plan(self, user_id, plan):
        self.activated.append((user_id, plan))
        if self.user:
            self.user["plan"] = plan
            self.user["plan_expiry"] = datetime.now(timezone.utc) + timedelta(days=30)

    def check_expired_plans(self):
        if self.user and self.user.get("plan") != "lite" and self.user.get("plan_expiry"):
            if self.user["plan_expiry"] < datetime.now(timezone.utc):
                return [self.user["user_id"]]
        return []

    def reset_expired_plan(self, user_id):
        self.reset_calls.append(user_id)
        if self.user and self.user.get("user_id") == user_id:
            self.user["plan"] = "lite"
            self.user["plan_expiry"] = None
        return True

    def atomic_spend_coins(self, user_id, cost, operation_type, status="pending"):
        # имитировать списание монет
        self.last_tx = {
            "user_id": user_id,
            "cost": cost,
            "operation_type": operation_type,
            "status": status,
        }
        return 1  # ID транзакции

    def add_transaction(self, *_, **__):
        raise NotImplementedError

    def update_transaction_status(self, *_, **__):
        raise NotImplementedError

    def add_refund_transaction(self, *_, **__):
        raise NotImplementedError


def stub_db(monkeypatch, initial_user=None):
    stub = StubDB(initial_user)
    monkeypatch.setattr(billing, "db", stub)
    return stub


def test_activate_plan_adds_coins_and_sets_expiry(monkeypatch):
    user = {
        "user_id": 1,
        "coins": 0,
        "plan": "lite",
        "plan_expiry": None,
        "admin_coins": 0,
    }
    stub = stub_db(monkeypatch, user)

    result = billing.activate_plan(1, "lite")
    assert result["coins"] == user["coins"] + billing.PLANS["lite"]["coins"]
    assert result["plan"] == "lite"
    assert result["plan_expiry"] is None

    result = billing.activate_plan(1, "std")
    assert result["plan"] == "std"
    assert result["coins"] == user["coins"] + billing.PLANS["lite"]["coins"] + billing.PLANS["std"]["coins"]
    expiry = result["plan_expiry"]
    assert isinstance(expiry, datetime)
    if expiry.tzinfo:
        now_ref = datetime.now(timezone.utc)
    else:
        now_ref = datetime.now(timezone.utc).replace(tzinfo=None)
    diff_days = (expiry - now_ref).days
    assert 28 <= diff_days <= 31

def test_check_subscription_resets_expired_plan(monkeypatch):
    expired_user = {
        "user_id": 2,
        "coins": 50,
        "plan": "std",
        "plan_expiry": datetime.now(timezone.utc) - timedelta(days=1),
    }
    stub = stub_db(monkeypatch, expired_user)

    # check_subscription должен сбросить план на 'lite' для истекшего пользователя
    updated = billing.check_subscription(expired_user)
    assert updated["plan"] == "lite"
    assert updated["plan_expiry"] is None
    assert stub.reset_calls == [2]


def test_apply_top_up_only_adds_coins(monkeypatch):
    user = {"user_id": 3, "coins": 10, "plan": "lite", "plan_expiry": None}
    stub = stub_db(monkeypatch, user)

    result = billing.apply_top_up(3, 40, "topup")
    assert result["coins"] == 50
    assert result["plan"] == "lite"
    assert stub.user["coins"] == 50


def test_transactions_logged_on_spend(monkeypatch):
    class SpendStub(StubDB):
        def __init__(self):
            super().__init__({"user_id": 4, "coins": 20, "plan": "lite", "plan_expiry": None})
            self.spend_calls = []

        def atomic_spend_coins(self, user_id, cost, operation_type, status="pending"):
            self.spend_calls.append((user_id, cost, operation_type, status))
            self.user["coins"] -= cost
            return len(self.spend_calls)

        def update_transaction_status(self, transaction_id, status):
            self.spend_calls.append(("status", transaction_id, status))

    stub = SpendStub()
    monkeypatch.setattr(billing, "db", stub)

    job_id = billing.hold_and_start(stub.user, "video")
    assert stub.spend_calls[0][:3] == (4, billing.COST_VIDEO, "video")
    billing.on_success(stub.user, job_id)
    assert stub.spend_calls[-1] == ("status", 1, "completed")
