from typing import Optional
from decimal import Decimal
from app.services.pricing import feature_cost_coins, cogs_usd, calculate_coin_rate_rub, calculate_coin_rate_rub_topup
from app.db.queries import execute_query, fetch_one, fetch_all

def get_balance(user_id: int) -> int:
    """Получить баланс монет пользователя"""
    result = fetch_one(
        "SELECT coins_balance FROM users_wallet WHERE user_id = %s",
        (user_id,)
    )
    return result['coins_balance'] if result else 0

def set_balance(user_id: int, new_balance: int) -> None:
    """Установить новый баланс монет пользователя"""
    execute_query(
        """
        INSERT INTO users_wallet (user_id, coins_balance) 
        VALUES (%s, %s) 
        ON CONFLICT (user_id) 
        DO UPDATE SET coins_balance = %s
        """,
        (user_id, new_balance, new_balance)
    )

def get_user_tariff_info(user_id: int) -> Optional[dict]:
    """Получить информацию о тарифе пользователя"""
    return fetch_one(
        "SELECT active_tariff, tariff_expires_at FROM users_wallet WHERE user_id = %s",
        (user_id,)
    )

def set_user_tariff(user_id: int, tariff_name: str, expires_at: str) -> None:
    """Установить тариф пользователя"""
    execute_query(
        """
        INSERT INTO users_wallet (user_id, active_tariff, tariff_expires_at) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) 
        DO UPDATE SET active_tariff = %s, tariff_expires_at = %s
        """,
        (user_id, tariff_name, expires_at, tariff_name, expires_at)
    )

def log_transaction(user_id: int, kind: str, coins_delta: int,
                   feature_key: Optional[str] = None,
                   rub_value: Optional[float] = None,
                   cogs_usd_value: Optional[float] = None) -> None:
    """Записать транзакцию в лог"""
    execute_query(
        """
        INSERT INTO wallet_transactions 
        (user_id, kind, feature_key, coins_delta, rub_value, cogs_usd, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """,
        (user_id, kind, feature_key, coins_delta, rub_value, cogs_usd_value)
    )

def charge_feature(user_id: int, feature_key: str) -> bool:
    """Списать монеты за использование функции"""
    cost = feature_cost_coins(feature_key)
    current_balance = get_balance(user_id)
    
    if current_balance < cost:
        return False
    
    # Получаем информацию о тарифе для расчета стоимости монеты
    tariff_info = get_user_tariff_info(user_id)
    coin_rate_rub = 16.0  # дефолтная стоимость монеты
    
    if tariff_info and tariff_info['active_tariff']:
        coin_rate_rub = calculate_coin_rate_rub(tariff_info['active_tariff'])
    
    # Списываем монеты
    new_balance = current_balance - cost
    set_balance(user_id, new_balance)
    
    # Логируем транзакцию
    log_transaction(
        user_id=user_id,
        kind="feature_charge",
        coins_delta=-cost,
        feature_key=feature_key,
        rub_value=round(cost * coin_rate_rub, 2),
        cogs_usd_value=float(cogs_usd(feature_key))
    )
    
    return True

def add_coins(user_id: int, coins: int, source: str, rub_value: Optional[float] = None) -> None:
    """Добавить монеты пользователю"""
    current_balance = get_balance(user_id)
    new_balance = current_balance + coins
    set_balance(user_id, new_balance)
    
    # Логируем транзакцию
    log_transaction(
        user_id=user_id,
        kind=source,
        coins_delta=coins,
        rub_value=rub_value
    )

def buy_tariff(user_id: int, tariff_name: str, rub_value: int) -> None:
    """Купить тариф"""
    from app.services.pricing import coins_for_tariff
    
    coins = coins_for_tariff(tariff_name)
    add_coins(user_id, coins, "tariff_purchase", rub_value)
    
    # Устанавливаем тариф на 30 дней
    from datetime import datetime, timedelta
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    set_user_tariff(user_id, tariff_name, expires_at)

def buy_topup(user_id: int, pack_coins: int) -> None:
    """Купить пакет пополнения"""
    from app.services.pricing import topup_price_rub
    
    rub_value = topup_price_rub(pack_coins)
    add_coins(user_id, pack_coins, "topup_purchase", rub_value)

def get_transaction_history(user_id: int, limit: int = 50) -> list:
    """Получить историю транзакций пользователя"""
    return fetch_all(
        """
        SELECT kind, feature_key, coins_delta, rub_value, cogs_usd, created_at
        FROM wallet_transactions 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """,
        (user_id, limit)
    )
