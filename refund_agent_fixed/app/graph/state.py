from typing import TypedDict, Literal, Optional


class RefundCaseState(TypedDict, total=False):
    thread_id: str
    image_path: str
    category: Literal['upi_failed', 'ecommerce_return']
    transaction_id: Optional[str]
    merchant_name: Optional[str]
    amount: Optional[float]
    transaction_date: Optional[str]
    upi_transaction_type: Optional[Literal['merchant_payment', 'person_to_person']]
    is_domestic: Optional[bool]
    is_evidence_valid: bool
    missing_info_prompt: str
    assessment_date: Optional[str]
    resolution_date: Optional[str]
    failure_attributable_to_customer: Optional[bool]
    rule_applicable: bool
    rule_reason: str
    tat_days: int
    deadline_passed: bool
    delay_days: int
    penalty_owed: float
    eligible_for_compensation: bool
    drafted_email: str
    approval_status: Literal['not_requested', 'approved', 'rejected']
    escalation_tier: Optional[Literal[1, 2]]
    escalation_reason: str
    status: Literal['pending', 'evidence_invalid', 'under_review', 'awaiting_approval', 'claim_dispatched', 'resolved', 'escalated', 'rejected', 'workflow_error']
    dispatch_error: str
    extraction_notes: str
