# -*- coding: utf-8 -*-
"""
Lightweight YooKassa integration layer.

In production, replace create_payment_link with real YooKassa API calls and
verify_webhook_signature with proper signature validation. The rest of the
module normalizes webhooks and applies business logic via wallet service.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional

from app.services.wallet import buy_tariff, buy_topup


SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("YOOKASSA_WEBHOOK_SECRET")


def create_payment_link(*, user_id: int, amount: int | float, description: str, plan: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Returns a payment URL. In test/dev, returns a recognizable test URL.

    metadata: optional custom dict. If plan is provided, metadata {"plan": plan, "type": "plan"} is used.
    """
    if plan:
        metadata = {"plan": plan, "type": "plan", **(metadata or {})}

    if not SHOP_ID or not SECRET_KEY:
        # Test URL recognizable by the UI
        return f"https://test_yookassa/pay/test_{user_id}_{int(float(amount))}"

    # NOTE: Implement real payment creation here using YooKassa SDK/API.
    # For now, still return a placeholder that doesn't include 'test_'
    return f"https://checkout.yookassa.ru/payments/{user_id}_{int(float(amount))}"


def verify_webhook_signature(payload: bytes, signature: Optional[str]) -> bool:
    """Verifies webhook signature if WEBHOOK_SECRET is set. Otherwise allow.
    YooKassa can use different validation strategies; adjust accordingly.
    """
    if not WEBHOOK_SECRET:
        return True
    if not signature:
        return False
    calc = hmac.new(WEBHOOK_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, signature)


def process_payment_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizes YooKassa webhook dict into our internal structure.
    Expected input keys: 'event', 'object': {'id','status','amount':{'value'}, 'metadata':{...}}
    """
    try:
        event = webhook_data.get("event")
        obj = webhook_data.get("object", {})
        payment_id = obj.get("id")
        amount_val = obj.get("amount", {}).get("value")
        amount = float(amount_val) if amount_val is not None else None
        metadata = obj.get("metadata", {}) or {}
        user_id = metadata.get("user_id") or metadata.get("uid")

        return {
            "event": event,
            "payment_id": payment_id,
            "amount": amount,
            "metadata": metadata,
            "user_id": user_id,
        }
    except Exception:
        return None


def process_successful_payment(payment: Dict[str, Any]) -> bool:
    """Applies business logic for a succeeded payment.
    - plan purchase: credit coins, set active_tariff and expiry
    - topup: credit coins
    """
    try:
        metadata = payment.get("metadata") or {}
        user_id = int(payment.get("user_id")) if payment.get("user_id") is not None else None
        if not user_id:
            return False

        if metadata.get("type") == "plan" or metadata.get("plan"):
            plan = metadata.get("plan")
            if not plan:
                return False
            buy_tariff(user_id, plan)
            return True

        if metadata.get("type") == "topup":
            coins = int(metadata.get("coins", 0))
            if coins <= 0:
                return False
            buy_topup(user_id, coins)
            return True

        # Unknown payment type
        return False
    except Exception:
        return False


