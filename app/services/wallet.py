from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List

from app.db.queries import db
from app.services.pricing import (
    feature_cost_coins,
    cogs_usd,
    calculate_coin_rate_rub,
    calculate_coin_rate_rub_topup,
    coins_for_tariff,
)


def get_balance(user_id: int) -> int:
    user = db.get_user(user_id) or {}
    return int(user.get("coins", 0))


def _insert_wallet_tx(user_id: int, kind: str, coins_delta: int, feature_key: Optional[str], rub_value: Optional[Decimal], cogs_value: Optional[Decimal]) -> None:
    if not db.ensure_connection():
        return
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wallet_transactions (user_id, kind, feature_key, coins_delta, rub_value, cogs_usd)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, kind, feature_key, coins_delta, (rub_value if rub_value is None else float(rub_value)), (cogs_value if cogs_value is None else float(cogs_value))),
            )
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise


def _update_wallet_balance(user_id: int, coins_delta: int) -> None:
    if not db.ensure_connection():
        return
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES (%s, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id,),
            )
            cursor.execute(
                """
                INSERT INTO users_wallet (user_id, coins_balance)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET coins_balance = users_wallet.coins_balance + EXCLUDED.coins_balance
                """,
                (user_id, coins_delta),
            )
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise


def charge_feature(user_id: int, feature_key: str, with_audio: Optional[bool] = None) -> bool:
    """Списывает монеты за функционал и логирует rub_value и cogs_usd.

    rub_value считается по текущей цене монеты для пользователя: если есть активная подписка (active_tariff не lite и не истек), используем её цену монеты,
    иначе используем самую выгодную цену из топапов по умолчанию в качестве оценки или реальную последнюю покупку (упрощённо берём минимальную из тарифов).
    """
    cost = feature_cost_coins(feature_key)

    # Баланс проверяем
    if get_balance(user_id) < cost:
        return False

    # Определяем ставку руб/монета: используем минимальную стоимость по активным тарифам как приблизительную
    # Точное отслеживание по последним покупкам можно внедрить позже
    coin_rate = min(calculate_coin_rate_rub(t) for t in ("lite", "standard", "pro"))
    rub_value = coin_rate * Decimal(cost)
    cogs = cogs_usd(feature_key)

    # Списываем баланс и пишем транзакцию
    _update_wallet_balance(user_id, -cost)
    _insert_wallet_tx(user_id, kind="feature_charge", coins_delta=-cost, feature_key=feature_key, rub_value=rub_value, cogs_value=cogs)
    return True


def refund_feature(user_id: int, feature_key: str, coins: int) -> None:
    """Возврат монет при технической ошибке выполнения операции."""
    if coins <= 0:
        return
    _update_wallet_balance(user_id, coins)
    # Для возврата rub_value/cogs_usd не указываем
    _insert_wallet_tx(user_id, kind="feature_refund", coins_delta=coins, feature_key=feature_key, rub_value=None, cogs_value=None)


def buy_tariff(user_id: int, tariff_name: str) -> None:
    coins = coins_for_tariff(tariff_name)
    rate = calculate_coin_rate_rub(tariff_name)
    rub_value = rate * Decimal(coins)

    # Начисляем монеты
    _update_wallet_balance(user_id, coins)

    # Обновляем активный тариф и срок
    if db.ensure_connection():
        try:
            with db.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users_wallet (user_id, active_tariff, tariff_expires_at, coins_balance)
                    VALUES (%s, %s, NOW() + INTERVAL '30 days', 0)
                    ON CONFLICT (user_id)
                    DO UPDATE SET active_tariff = EXCLUDED.active_tariff, tariff_expires_at = EXCLUDED.tariff_expires_at
                    """,
                    (user_id, tariff_name),
                )
            db.connection.commit()
        except Exception:
            db.connection.rollback()
            raise

    _insert_wallet_tx(user_id, kind="tariff_purchase", coins_delta=coins, feature_key=None, rub_value=rub_value, cogs_value=None)


def buy_topup(user_id: int, coins: int) -> None:
    rate = calculate_coin_rate_rub_topup(coins)
    rub_value = rate * Decimal(coins)
    _update_wallet_balance(user_id, coins)
    _insert_wallet_tx(user_id, kind="topup_purchase", coins_delta=coins, feature_key=None, rub_value=rub_value, cogs_value=None)


def get_user_tariff_info(user_id: int) -> Dict:
    user = db.get_user(user_id) or {}
    return {
        "active_tariff": user.get("plan", "lite"),
        "tariff_expires_at": user.get("plan_expiry"),
        "coins": user.get("coins", 0),
    }


def get_transaction_history(user_id: int, limit: int = 10) -> List[Dict]:
    if not db.ensure_connection():
        return []
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, kind, feature_key, coins_delta, rub_value, cogs_usd, created_at
                FROM wallet_transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r[0],
                    "user_id": r[1],
                    "kind": r[2],
                    "feature_key": r[3],
                    "coins_delta": int(r[4] or 0),
                    "rub_value": float(r[5]) if r[5] is not None else None,
                    "cogs_usd": float(r[6]) if r[6] is not None else None,
                    "created_at": r[7],
                })
            return result
    except Exception:
        return []


def sync_pricing() -> str:
    # В текущей реализации данные в коде; «перезагрузка» не требуется.
    # Функция оставлена для будущего: например, если будем читать из внешнего источника.
    return "✅ Pricing reloaded"


