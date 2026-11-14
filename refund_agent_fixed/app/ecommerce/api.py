from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import create_case, get_case, update_case
from app.ecommerce.graph.workflow import refund_graph
from app.ecommerce.refund_executor import get_refund_history


router = APIRouter(prefix="/ecommerce", tags=["E-commerce Refunds"])


class ECommerceRefundRequest(BaseModel):
    customer_id: str
    order_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1)
    reason: str = "other"
    description: str = ""


class ECommerceReviewRequest(BaseModel):
    thread_id: str
    approved: bool


def public_result(state):
    keys = [
        "customer_id", "order_id", "product_id", "quantity",
        "reason", "order_verified", "verification_message",
        "eligible", "refund_amount", "policy_message",
        "risk_score", "risk_level", "risk_flags",
        "decision", "decision_reason", "refund_status",
        "refund_reference", "idempotency_key", "audit_log",
    ]
    return {key: state[key] for key in keys if key in state}


@router.post("/start")
def start_ecommerce_refund(request: ECommerceRefundRequest):
    thread_id = str(uuid4())

    initial_state = {
        "request_id": thread_id,
        "customer_id": request.customer_id,
        "order_id": request.order_id,
        "product_id": request.product_id,
        "quantity": request.quantity,
        "reason": request.reason,
        "description": request.description,
    }

    try:
        create_case({
            "thread_id": thread_id,
            "image_path": "",
            "category": "ecommerce_return",
            "status": "processing",
            "approval_status": "not_requested",
            "state": initial_state,
        })

        result = refund_graph.invoke(initial_state)

        if result.get("refund_status") == "success":
            status = "refunded"
            approval_status = "not_required"
        elif result.get("refund_status") == "pending_review":
            status = "awaiting_approval"
            approval_status = "awaiting_approval"
        else:
            status = "rejected"
            approval_status = "not_required"

        update_case(thread_id, {
            "status": status,
            "approval_status": approval_status,
            "state": result,
        })

        return {
            "thread_id": thread_id,
            "status": status,
            "approval_status": approval_status,
            "result": public_result(result),
        }

    except Exception as exc:
        update_case(thread_id, {
            "status": "workflow_error",
            "state": {**initial_state, "error": str(exc)},
        })
        raise HTTPException(status_code=500, detail=f"E-commerce workflow failed: {exc}")


@router.get("/case/{thread_id}")
def get_ecommerce_case(thread_id: str):
    case = get_case(thread_id)

    if not case or case["category"] != "ecommerce_return":
        raise HTTPException(status_code=404, detail="E-commerce case not found.")

    return {
        "thread_id": thread_id,
        "status": case["status"],
        "approval_status": case["approval_status"],
        "result": public_result(case.get("state", {})),
    }


@router.post("/approve")
def review_ecommerce_case(request: ECommerceReviewRequest):
    case = get_case(request.thread_id)

    if not case or case["category"] != "ecommerce_return":
        raise HTTPException(status_code=404, detail="E-commerce case not found.")

    if case["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Case is not awaiting human review.")

    if case["approval_status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Case has already been reviewed.")

    if not request.approved:
        update_case(request.thread_id, {
            "status": "rejected",
            "approval_status": "rejected",
            "state": {
                **case.get("state", {}),
                "decision": "rejected",
                "decision_reason": "Rejected by human reviewer.",
                "refund_status": "not_started",
            },
        })
        return {
            "thread_id": request.thread_id,
            "status": "rejected",
            "approval_status": "rejected",
            "message": "Refund request rejected. No refund was executed.",
        }

    state = {**case.get("state", {}), "human_approved": True}

    try:
        result = refund_graph.invoke(state)

        status = "refunded" if result.get("refund_status") == "success" else "workflow_error"

        update_case(request.thread_id, {
            "status": status,
            "approval_status": "approved",
            "state": result,
        })

        return {
            "thread_id": request.thread_id,
            "status": status,
            "approval_status": "approved",
            "result": public_result(result),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Approval execution failed: {exc}")


@router.get("/refund-history")
def ecommerce_refund_history():
    history = get_refund_history()
    return {"total": len(history), "refunds": history}
