import pytest
from app.rules.tat_engine import calculate_tat


def test_merchant_payment_delayed():
    result = calculate_tat('upi_failed', '2026-11-01', '2026-11-08', upi_transaction_type='merchant_payment')
    assert result.tat_days == 5 and result.delay_days == 2 and result.penalty_owed == 200
    assert result.eligible_for_compensation is True


def test_person_to_person_delayed():
    result = calculate_tat('upi_failed', '2026-11-01', '2026-11-03', upi_transaction_type='person_to_person')
    assert result.tat_days == 1 and result.delay_days == 1 and result.penalty_owed == 100


def test_no_penalty_on_deadline():
    result = calculate_tat('upi_failed', '2026-11-01', '2026-11-06', upi_transaction_type='merchant_payment')
    assert result.delay_days == 0 and result.penalty_owed == 0 and not result.eligible_for_compensation


def test_ecommerce_return_not_covered_by_upi_rule():
    result = calculate_tat('ecommerce_return', '2026-11-01', '2026-11-10')
    assert not result.rule_applicable and result.penalty_owed == 0 and result.tat_days is None


def test_customer_attributable_failure():
    result = calculate_tat('upi_failed', '2026-11-01', '2026-11-10', upi_transaction_type='merchant_payment', failure_attributable_to_customer=True)
    assert not result.rule_applicable and result.penalty_owed == 0


def test_invalid_transaction_type():
    with pytest.raises(ValueError):
        calculate_tat('upi_failed', '2026-11-01', '2026-11-10', upi_transaction_type='unknown')


def test_completed_late_reversal():
    result = calculate_tat('upi_failed', '2026-11-01', '2026-11-10', resolution_date='2026-11-09', upi_transaction_type='merchant_payment')
    assert result.delay_days == 3 and result.penalty_owed == 300


def test_invalid_date():
    with pytest.raises(ValueError):
        calculate_tat('upi_failed', 'not-a-date', '2026-11-10', upi_transaction_type='merchant_payment')
