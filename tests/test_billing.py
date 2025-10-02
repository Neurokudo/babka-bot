import copy

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import billing


class StubDB:
    def __init__(self):
        self.atomic_calls = []
        self.updated = []
        self.refunds = []
        self.saved = []

    def atomic_spend_coins(self, user_id, cost, operation_type, status="pending"):
        call = {
            "user_id": user_id,
            "cost": cost,
            "operation_type": operation_type,
            "status": status,
        }
        self.atomic_calls.append(call)
        return len(self.atomic_calls)

    def update_transaction_status(self, transaction_id, status):
        self.updated.append((transaction_id, status))

    def add_refund_transaction(self, user_id, amount, original_transaction_id=None):
        self.refunds.append(
            {
                "user_id": user_id,
                "amount": amount,
                "metadata": {"original_transaction_id": original_transaction_id},
            }
        )
        return len(self.refunds)

    def save_user(self, user_id, user_data):
        self.saved.append((user_id, copy.deepcopy(user_data)))


def make_user(coins=100):
    return {
        "user_id": 1,
        "coins": coins,
        "jobs": {},
        "last_job": None,
    }


@pytest.fixture
def stub_db(monkeypatch):
    stub = StubDB()
    monkeypatch.setattr(billing, "db", stub)
    return stub


def test_video_generation_charges_10_coins(stub_db):
    user = make_user(coins=30)

    job_id = billing.hold_and_start(user, "video")

    assert stub_db.atomic_calls[-1]["cost"] == billing.COST_VIDEO == 10
    assert user["coins"] == 20
    assert user["jobs"][job_id]["coin_cost"] == 10

    billing.on_success(user, job_id)
    assert stub_db.updated[-1] == (1, "completed")


def test_photo_basic_and_premium_costs(stub_db):
    user = make_user(coins=10)

    job_basic = billing.hold_and_start(user, "transform", quality="basic")
    assert user["coins"] == 9
    assert user["jobs"][job_basic]["coin_cost"] == billing.COST_TRANSFORM == 1

    job_premium = billing.hold_and_start(user, "transform", quality="premium")
    assert user["coins"] == 7  # 9 - 2
    assert user["jobs"][job_premium]["coin_cost"] == billing.COST_TRANSFORM_PREMIUM == 2


def test_tryon_costs_one_coin(stub_db):
    user = make_user(coins=5)

    job_id = billing.hold_and_start(user, "tryon")

    assert user["coins"] == 4
    assert user["jobs"][job_id]["coin_cost"] == billing.COST_TRYON == 1


def test_json_mode_costs_like_video(stub_db):
    user = make_user(coins=20)

    job_id = billing.hold_and_start(user, "json")

    assert user["coins"] == 10
    assert user["jobs"][job_id]["coin_cost"] == billing.COST_VIDEO


def test_refund_returns_coins_and_logs(stub_db):
    user = make_user(coins=15)
    job_id = billing.hold_and_start(user, "transform", quality="basic")

    assert user["coins"] == 14

    billing.on_error(user, job_id, reason="timeout")

    # coins refunded
    assert user["coins"] == 15
    # refund transaction recorded
    assert stub_db.refunds[-1]["amount"] == 1
