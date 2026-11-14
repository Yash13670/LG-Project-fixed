from datetime import date
from hashlib import sha256

from app.ecommerce.models import RefundRequest, RefundReason
from app.ecommerce.graph.state import RefundAgentState
from app.ecommerce.seed_data import build_mock_store
from app.ecommerce.refund_policy import evaluate_refund_request
from app.ecommerce.refund_executor import execute_mock_refund


def verify_order_node(state: RefundAgentState):
    store = build_mock_store()
    order = store.get_order(state["order_id"])

    if not order:
        return {
            "order_verified": False,
            "verification_message": "Order not found.",
        }

    if order.customer_id != state["customer_id"]:
        return {
            "order_verified": False,
            "verification_message": "Customer does not own this order.",
        }

    return {
        "order_verified": True,
        "verification_message": "Order verified successfully.",
    }


def policy_check_node(state: RefundAgentState):
    store = build_mock_store()
    order = store.get_order(state["order_id"])

    raw_reason = state.get("reason", "other")

    try:
        reason = RefundReason(raw_reason)
    except ValueError:
        reason = RefundReason.OTHER

    request = RefundRequest(
        request_id=state.get(
            "request_id",
            f"{state['order_id']}-{state['product_id']}-{state['customer_id']}",
        ),
        order_id=state["order_id"],
        customer_id=state["customer_id"],
        product_id=state["product_id"],
        quantity=state.get("quantity", 1),
        reason=reason,
    )

    result = evaluate_refund_request(
        order=order,
        request=request,
        today=date.today(),
    )

    return {
        "eligible": result.eligible,
        "refund_amount": float(result.approved_amount or 0),
        "policy_message": result.explanation,
    }


def risk_assessment_node(state: RefundAgentState):
    flags = []
    score = 0
    amount = state.get("refund_amount", 0)

    if amount >= 5000:
        score += 50
        flags.append("High refund amount")
    elif amount >= 2000:
        score += 20
        flags.append("Elevated refund amount")

    if not state.get("order_verified"):
        score += 100
        flags.append("Order verification failed")

    if not state.get("eligible"):
        score += 100
        flags.append("Refund policy check failed")

    if score >= 50:
        level = "high"
    elif score >= 20:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": min(score, 100),
        "risk_level": level,
        "risk_flags": flags,
    }


def decision_node(state: RefundAgentState):
    if not state.get("order_verified"):
        return {
            "decision": "rejected",
            "decision_reason": "Order verification failed.",
        }

    if not state.get("eligible"):
        return {
            "decision": "rejected",
            "decision_reason": state.get("policy_message", "Not eligible."),
        }

    if state.get("human_approved") is True:
        return {
            "decision": "auto_approve",
            "decision_reason": "Human approval received.",
        }

    if state.get("risk_level") in ("high", "medium"):
        return {
            "decision": "human_review",
            "decision_reason": "Request requires manual review.",
        }

    return {
        "decision": "auto_approve",
        "decision_reason": "Low-risk request passed all checks.",
    }


def execute_refund_node(state: RefundAgentState):
    # A stable key prevents the same request from being refunded twice.
    raw_key = "|".join([
        state["customer_id"],
        state["order_id"],
        state["product_id"],
        str(state.get("quantity", 1)),
        state.get("reason", "other"),
    ])
    idempotency_key = sha256(raw_key.encode()).hexdigest()

    record = execute_mock_refund(
        idempotency_key=idempotency_key,
        order_id=state["order_id"],
        customer_id=state["customer_id"],
        amount=state.get("refund_amount", 0),
        reason=state.get("reason", "other"),
    )

    return {
        "refund_status": "success",
        "refund_reference": record["refund_reference"],
        "idempotency_key": idempotency_key,
        "audit_log": [{
            "event": "mock_refund_executed",
            "refund_reference": record["refund_reference"],
            "amount": record["amount"],
            "duplicate": record["duplicate"],
            "timestamp": record["created_at"],
        }],
    }


def pending_review_node(state: RefundAgentState):
    return {
        "refund_status": "pending_review",
        "refund_reference": None,
        "audit_log": [{
            "event": "human_review_required",
            "reason": state.get("decision_reason", "Manual review required."),
            "risk_level": state.get("risk_level", "unknown"),
        }],
    }
