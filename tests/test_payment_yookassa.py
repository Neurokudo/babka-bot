# -*- coding: utf-8 -*-
"""
Тесты для payment_yookassa.py
"""

import pytest
from unittest.mock import Mock, patch
from payment_yookassa import process_successful_payment, apply_refund


class TestPaymentYooKassa:
    """Тесты для обработки платежей YooKassa"""

    @patch('app.db.queries.db')
    @patch('app.billing.plans.activate_plan')
    @patch('app.billing.apply_top_up')
    def test_process_successful_payment_tariff(self, mock_apply_top_up, mock_activate_plan, mock_db):
        """Тест: обработка успешного платежа за тариф"""
        payment_data = {
            "payment_id": "test_payment_123",
            "user_id": "12345",
            "metadata": {
                "plan": "standard"
            }
        }

        result = process_successful_payment(payment_data)

        assert result is True
        mock_db.update_payment_status.assert_called_once_with("test_payment_123", "succeeded")
        mock_activate_plan.assert_called_once_with("12345", "standard")

    @patch('app.db.queries.db')
    @patch('app.billing.plans.activate_plan')
    @patch('app.billing.apply_top_up')
    def test_process_successful_payment_coins(self, mock_apply_top_up, mock_activate_plan, mock_db):
        """Тест: обработка успешного платежа за монеты"""
        payment_data = {
            "payment_id": "test_payment_456",
            "user_id": "67890",
            "metadata": {
                "type": "coins",
                "coins": "100"
            }
        }

        result = process_successful_payment(payment_data)

        assert result is True
        mock_db.update_payment_status.assert_called_once_with("test_payment_456", "succeeded")
        mock_apply_top_up.assert_called_once_with("67890", 100, "coins_topup")
        mock_activate_plan.assert_not_called()

    @patch('app.db.queries.db')
    @patch('app.billing.plans.activate_plan')
    @patch('app.billing.apply_top_up')
    def test_process_successful_payment_unknown_plan(self, mock_apply_top_up, mock_activate_plan, mock_db):
        """Тест: обработка платежа с неизвестным планом"""
        payment_data = {
            "payment_id": "test_payment_789",
            "user_id": "11111",
            "metadata": {
                "plan": "unknown_plan"
            }
        }

        result = process_successful_payment(payment_data)

        assert result is True
        mock_db.update_payment_status.assert_called_once_with("test_payment_789", "succeeded")
        mock_activate_plan.assert_not_called()
        mock_apply_top_up.assert_not_called()

    @patch('app.db.queries.db')
    @patch('app.billing.plans.activate_plan')
    @patch('app.billing.apply_top_up')
    def test_process_successful_payment_missing_data(self, mock_apply_top_up, mock_activate_plan, mock_db):
        """Тест: обработка платежа с отсутствующими данными"""
        payment_data = {
            "payment_id": "test_payment_000",
            # user_id отсутствует
            "metadata": {}
        }

        result = process_successful_payment(payment_data)

        assert result is False
        mock_db.update_payment_status.assert_not_called()
        mock_activate_plan.assert_not_called()
        mock_apply_top_up.assert_not_called()

    @patch('app.db.queries.db')
    @patch('app.billing.coins.refund_coins')
    def test_apply_refund(self, mock_refund_coins, mock_db):
        """Тест: обработка возврата платежа"""
        payment_data = {
            "payment_id": "test_payment_refund",
            "user_id": "99999",
            "amount": 150.0  # 150 рублей
        }

        result = apply_refund(payment_data)

        assert result is True
        mock_db.update_payment_status.assert_called_once_with("test_payment_refund", "refunded")
        # 150 рублей / 15 = 10 монет
        mock_refund_coins.assert_called_once_with("99999", 10, "test_payment_refund")

    @patch('app.db.queries.db')
    @patch('app.billing.coins.refund_coins')
    def test_apply_refund_missing_data(self, mock_refund_coins, mock_db):
        """Тест: обработка возврата с отсутствующими данными"""
        payment_data = {
            "payment_id": "test_payment_refund_2",
            # user_id отсутствует
            "amount": 100.0
        }

        result = apply_refund(payment_data)

        assert result is False
        mock_db.update_payment_status.assert_not_called()
        mock_refund_coins.assert_not_called()

    @patch('app.db.queries.db')
    @patch('app.billing.coins.refund_coins')
    def test_apply_refund_zero_amount(self, mock_refund_coins, mock_db):
        """Тест: обработка возврата с нулевой суммой"""
        payment_data = {
            "payment_id": "test_payment_refund_3",
            "user_id": "88888",
            "amount": 0.0
        }

        result = apply_refund(payment_data)

        assert result is True
        mock_db.update_payment_status.assert_called_once_with("test_payment_refund_3", "refunded")
        mock_refund_coins.assert_not_called()  # 0 / 15 = 0 монет


if __name__ == "__main__":
    pytest.main([__file__])
