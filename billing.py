# -*- coding: utf-8 -*-
"""Биллинг Babka Bot: единая монетная система и управление тарифами."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from config import COST_TRANSFORM, COST_TRANSFORM_PREMIUM, COST_TRYON, COST_VIDEO, PLANS, LOW_COINS_THRESHOLD
from database import db

State = Dict[str, Any]


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def can_spend(user: State, cost: int) -> bool:
    return user.get("coins", 0) >= cost


def check_subscription(user_or_id) -> State:
    """Проверяет срок действия тарифа и при необходимости сбрасывает его на lite."""
    if isinstance(user_or_id, dict):
        user = user_or_id
        user_id = user.get("user_id")
    else:
        user_id = user_or_id
        user = None

    if not user_id:
        return user or {}

    if user is None:
        user = db.get_user(user_id) or {"user_id": user_id, "plan": "lite", "plan_expiry": None, "coins": 0}

    plan = user.get("plan", "lite")
    plan_expiry = user.get("plan_expiry")

    if plan != "lite" and plan_expiry:
        try:
            expiry_dt = plan_expiry if isinstance(plan_expiry, datetime) else datetime.fromisoformat(str(plan_expiry).replace("Z", "+00:00"))
            if expiry_dt < _now_utc():
                db.reset_expired_plan(user_id)
                user["plan"] = "lite"
                user["plan_expiry"] = None
        except Exception:
            pass

    return user


# ---------------------------------------------------------------------------
# Основное списание / возврат
# ---------------------------------------------------------------------------

def _base_cost(job_type: str, quality: str = "basic", extra_cost: int = 0) -> int:
    if job_type == "transform":
        base = COST_TRANSFORM_PREMIUM if quality == "premium" else COST_TRANSFORM
    elif job_type == "tryon":
        base = COST_TRYON
    else:  # video и json
        base = COST_VIDEO
    return base + max(0, extra_cost)


def hold_and_start(user: State, job_type: str, quality: str = "basic", extra_cost: int = 0) -> str:
    user = check_subscription(user)
    cost = _base_cost(job_type, quality, extra_cost)

    tx_id = db.atomic_spend_coins(user["user_id"], cost, operation_type=job_type)
    if tx_id is None:
        raise ValueError("NO_COINS")

    user["coins"] = max(user.get("coins", 0) - cost, 0)

    jobs = user.setdefault("jobs", {})
    job_id = f"{job_type}:{tx_id}"
    jobs[job_id] = {
        "type": job_type,
        "operation": job_type,
        "coin_cost": cost,
        "status": "pending",
        "quality": quality,
        "transaction_id": tx_id,
        "retry_used": 0,
        "created_at": _now_utc().isoformat(),
    }
    user["last_job"] = jobs[job_id]
    return job_id


def on_success(user: State, job_id: str) -> None:
    job = user.get("jobs", {}).get(job_id)
    if not job:
        return
    job["status"] = "completed"
    job["completed_at"] = _now_utc().isoformat()
    tx_id = job.get("transaction_id")
    if tx_id:
        db.update_transaction_status(tx_id, "completed")
    db.save_user(user["user_id"], user)


def on_error(user: State, job_id: str, reason: str = "error") -> None:
    job = user.get("jobs", {}).get(job_id)
    if not job or job.get("status") != "pending":
        return

    cost = job.get("coin_cost", 0)
    tx_id = job.get("transaction_id")

    if cost > 0:
        user["coins"] = user.get("coins", 0) + cost
        db.add_refund_transaction(user["user_id"], cost, tx_id)
        if tx_id:
            db.update_transaction_status(tx_id, "refunded")

    job["status"] = "error"
    job["error_at"] = _now_utc().isoformat()
    db.save_user(user["user_id"], user)


def retry(user: State, job_id: str) -> bool:
    """Ретраи выполняют новое списание монет."""
    job = user.get("jobs", {}).get(job_id)
    if not job:
        return False

    job_type = job.get("type", "video")
    quality = job.get("quality", "basic")
    new_job_id = hold_and_start(user, job_type, quality)
    job.update(user["jobs"][new_job_id])
    return True


def get_retry_cost(user: State, job_id: str) -> int:
    job = user.get("jobs", {}).get(job_id)
    return job.get("coin_cost", COST_VIDEO) if job else COST_VIDEO


def can_retry(user: State, job_id: str) -> bool:
    job = user.get("jobs", {}).get(job_id)
    if not job:
        return False
    return can_spend(user, job.get("coin_cost", COST_VIDEO))


def check_low_coins(user: State, threshold: int = LOW_COINS_THRESHOLD) -> bool:
    return user.get("coins", 0) < threshold


# ---------------------------------------------------------------------------
# Тарифы и пополнения
# ---------------------------------------------------------------------------

def activate_plan(user_id: int, plan_key: str) -> Optional[Dict[str, Any]]:
    plan = PLANS.get(plan_key)
    if not plan:
        return None

    user = db.get_user(user_id) or {"user_id": user_id, "coins": 0, "plan": "lite", "plan_expiry": None}
    check_subscription(user)

    coins_before = user.get("coins", 0)
    coins_after = coins_before + plan.get("coins", 0)
    expiry_dt = (_now_utc() + timedelta(days=30)).replace(tzinfo=None) if plan_key != "lite" else None

    user.update({
        "coins": coins_after,
        "plan": plan_key,
        "plan_expiry": expiry_dt,
    })
    db.save_user(user_id, user)
    db.activate_plan(user_id, plan_key)
    return user


def apply_top_up(user_id: int, coins: int, label: str) -> Dict[str, Any]:
    user = db.get_user(user_id) or {"user_id": user_id, "coins": 0}
    user["coins"] = user.get("coins", 0) + coins
    db.save_user(user_id, user)
    return user


def spend_tax(user: State, amount: int, label: str) -> bool:
    tx = db.atomic_spend_coins(user.get("user_id"), amount, label)
    if tx is None:
        return False
    user["coins"] = max(user.get("coins", 0) - amount, 0)
    return True


def can_generate_video(user: State) -> bool:
    return can_spend(check_subscription(user), COST_VIDEO)


def can_generate_photo(user: State, cost: Optional[int] = None) -> bool:
    return can_spend(check_subscription(user), cost if cost is not None else COST_TRANSFORM)


def can_generate_tryon(user: State) -> bool:
    return can_spend(check_subscription(user), COST_TRYON)


def can_generate_json(user: State) -> bool:
    return can_spend(check_subscription(user), COST_VIDEO)


def check_and_reset_expired_plans() -> list[int]:
    expired = db.check_expired_plans()
    reset = []
    for user_id in expired:
        if db.reset_expired_plan(user_id):
            reset.append(user_id)
    return reset
