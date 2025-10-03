# -*- coding: utf-8 -*-
"""
Тонкий billing-слой для main.py: проверка баланса, холд/списание, ретраи и подписки.
Все реальные списания/начисления выполняются через app.services.wallet.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, Optional

from app.services.pricing import feature_cost_coins
from app.services.wallet import get_balance, charge_feature, buy_tariff, buy_topup, refund_feature
from app.db.queries import db


LOW_COINS_THRESHOLD = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def check_low_coins(user: Dict) -> bool:
    uid = int(user.get("user_id"))
    balance = get_balance(uid)
    return balance <= LOW_COINS_THRESHOLD


def can_spend(user: Dict, cost: int) -> bool:
    """Проверка, достаточно ли монет у пользователя для списания cost."""
    uid = int(user.get("user_id"))
    return get_balance(uid) >= int(cost)


def _feature_key_for(kind: str, st: Dict, quality: Optional[str] = None) -> str:
    if kind == "video" or kind == "json":
        with_audio = bool(st.get("with_audio", True))
        return "video_8s_audio" if with_audio else "video_8s_mute"
    if kind == "transform":
        return "image_basic"
    if kind == "tryon":
        return "virtual_tryon"
    return "image_basic"


def _can_afford(uid: int, cost: int) -> bool:
    return get_balance(uid) >= cost


def can_generate_video(st: Dict) -> bool:
    uid = int(st.get("user_id"))
    key = _feature_key_for("video", st)
    cost = feature_cost_coins(key)
    return _can_afford(uid, cost)


def can_generate_photo(st: Dict, cost: int) -> bool:
    uid = int(st.get("user_id"))
    return _can_afford(uid, cost)


def can_generate_tryon(st: Dict) -> bool:
    uid = int(st.get("user_id"))
    cost = feature_cost_coins("virtual_tryon")
    return _can_afford(uid, cost)


def can_generate_json(st: Dict) -> bool:
    uid = int(st.get("user_id"))
    cost = feature_cost_coins("video_8s_audio")
    return _can_afford(uid, cost)


def hold_and_start(st: Dict, kind: str, quality: Optional[str] = None) -> str:
    """Списывает монеты через wallet и создает запись о задаче в памяти пользователя.
    Возвращает job_id (строка). Бросает ValueError при нехватке монет.
    """
    uid = int(st.get("user_id"))
    feature_key = _feature_key_for(kind, st, quality)
    cost = feature_cost_coins(feature_key)
    if not _can_afford(uid, cost):
        raise ValueError("insufficient_funds")

    ok = charge_feature(uid, feature_key)
    if not ok:
        raise ValueError("charge_failed")

    job_id = f"{uid}_{kind}_{int(time.time()*1000)}"
    st.setdefault("jobs", {})
    st["jobs"][job_id] = {
        "coin_cost": cost,
        "feature_key": feature_key,
        "status": "running",
    }
    st["current_job_id"] = job_id
    return job_id


def on_success(st: Dict, job_id: str) -> None:
    job = st.get("jobs", {}).get(job_id)
    if job:
        job["status"] = "succeeded"


def on_error(st: Dict, job_id: str, reason: str = "error") -> None:
    job = st.get("jobs", {}).get(job_id)
    if job:
        job["status"] = reason
        # Возврат монет при технической ошибке
        uid = int(st.get("user_id"))
        coins = int(job.get("coin_cost", 0))
        feature_key = str(job.get("feature_key", ""))
        if coins > 0:
            refund_feature(uid, feature_key, coins)


def get_retry_cost(st: Dict, job_id: str) -> int:
    job = st.get("jobs", {}).get(job_id) or {}
    feature_key = job.get("feature_key") or _feature_key_for("video", st)
    return feature_cost_coins(feature_key)


def can_retry(st: Dict, job_id: str) -> bool:
    uid = int(st.get("user_id"))
    return _can_afford(uid, get_retry_cost(st, job_id))


def retry(st: Dict, job_id: str) -> bool:
    uid = int(st.get("user_id"))
    cost = get_retry_cost(st, job_id)
    job = st.get("jobs", {}).get(job_id)
    feature_key = (job or {}).get("feature_key") or _feature_key_for("video", st)
    if not _can_afford(uid, cost):
        return False
    ok = charge_feature(uid, feature_key)
    if ok and job:
        job["coin_cost"] = job.get("coin_cost", 0) + cost
    return ok


def activate_plan(user_id: int, plan: str) -> Dict:
    buy_tariff(int(user_id), plan)
    return {"ok": True}


def apply_top_up(user_id: int, coins: int) -> Dict:
    buy_topup(int(user_id), int(coins))
    return {"ok": True}


def check_subscription(user: Dict) -> Dict:
    plan = user.get("plan", "lite")
    expiry = user.get("plan_expiry")
    try:
        if plan and plan != "lite" and expiry:
            expiry_dt = expiry if isinstance(expiry, datetime) else datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
            if expiry_dt <= _now():
                user["plan"] = "lite"
                user["plan_expiry"] = None
    except Exception:
        pass
    return user


def check_and_reset_expired_plans() -> list[int]:
    ids = db.check_expired_plans() or []
    for uid in ids:
        try:
            db.reset_expired_plan(uid)
        except Exception:
            pass
    return ids


