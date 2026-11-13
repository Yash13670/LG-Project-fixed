from datetime import date, timedelta
from dataclasses import dataclass
from typing import Optional, Union

DateInput = Union[str, date]
COMPENSATION_PER_DAY = 100
TAT_RULES = {
    'merchant_payment': {'tat_days': 5, 'description': 'UPI merchant payment: confirmation not received'},
    'person_to_person': {'tat_days': 1, 'description': 'UPI fund transfer: beneficiary not credited'},
}


@dataclass(frozen=True)
class TATResult:
    rule_applicable: bool
    tat_days: Optional[int]
    deadline_date: Optional[date]
    deadline_passed: bool
    delay_days: int
    penalty_owed: int
    eligible_for_compensation: bool
    rule_reason: str


def parse_date(value: DateInput) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError('Invalid date. Use YYYY-MM-DD format.')


def calculate_tat(category: str, transaction_date: DateInput, assessment_date: DateInput,
                  upi_transaction_type: Optional[str] = None,
                  resolution_date: Optional[DateInput] = None,
                  is_domestic: bool = True,
                  failure_attributable_to_customer: bool = False) -> TATResult:
    txn_date = parse_date(transaction_date)
    check_date = parse_date(assessment_date)
    actual_resolution = parse_date(resolution_date) if resolution_date is not None else None
    if check_date < txn_date:
        raise ValueError('Assessment date cannot be before transaction date.')
    if actual_resolution is not None:
        if actual_resolution < txn_date:
            raise ValueError('Resolution date cannot be before transaction date.')
        if actual_resolution > check_date:
            raise ValueError('Resolution date cannot be after assessment date.')
    if category == 'ecommerce_return':
        return TATResult(False, None, None, False, 0, 0, False,
                         'RBI UPI failed-transaction TAT does not automatically apply to e-commerce returns. A separate applicable policy must be checked.')
    if category != 'upi_failed':
        raise ValueError('Unsupported transaction category.')
    if upi_transaction_type not in TAT_RULES:
        raise ValueError('Specify merchant_payment or person_to_person.')
    rule = TAT_RULES[upi_transaction_type]
    tat_days = rule['tat_days']
    deadline = txn_date + timedelta(days=tat_days)
    effective_date = actual_resolution or check_date
    delay_days = max(0, (effective_date - deadline).days)
    deadline_passed = effective_date > deadline
    applicable = is_domestic and not failure_attributable_to_customer
    if not applicable:
        reason = 'The supplied transaction circumstances do not meet the configured RBI framework eligibility conditions. Manual review is required.'
        penalty, eligible = 0, False
    else:
        penalty = delay_days * COMPENSATION_PER_DAY
        eligible = delay_days > 0
        reason = (f"{rule['description']}. The TAT of T+{tat_days} was exceeded by {delay_days} calendar days. Calculated compensation: ₹{penalty}." if eligible
                  else f"{rule['description']}. The T+{tat_days} deadline has not been exceeded.")
    return TATResult(applicable, tat_days, deadline, deadline_passed, delay_days, penalty, eligible, reason)
