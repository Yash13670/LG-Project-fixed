from typing import TypedDict, Optional, Literal


class RefundAgentState(TypedDict, total=False):
    customer_id: str
    order_id: str
    product_id: str
    quantity: int
    reason: str
    description: str
    request_id: str

    order_verified: bool
    verification_message: str

    eligible: bool
    refund_amount: float
    policy_message: str

    risk_score: int
    risk_level: Literal["low", "medium", "high"]
    risk_flags: list[str]

    decision: Literal["auto_approve", "human_review", "rejected"]
    decision_reason: str
    human_approved: bool

    refund_status: Literal["not_started", "success", "failed", "pending_review"]
    refund_reference: Optional[str]
    idempotency_key: str
    audit_log: list[dict]
    errors: list[str]
