from app.ecommerce.graph.workflow import refund_graph
from app.ecommerce.refund_executor import (
    get_refund_history,
    clear_mock_refund_ledger,
)


def test_low_risk_refund_executes():
    clear_mock_refund_ledger()

    result = refund_graph.invoke({
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "product_id": "P200",
        "quantity": 1,
        "reason": "damaged",
    })

    assert result["decision"] == "auto_approve"
    assert result["refund_status"] == "success"
    assert result["refund_reference"].startswith("MOCK-REF-")


def test_medium_risk_goes_to_human_review():
    clear_mock_refund_ledger()

    result = refund_graph.invoke({
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "product_id": "P100",
        "quantity": 1,
        "reason": "damaged",
    })

    assert result["decision"] == "human_review"
    assert result["refund_status"] == "pending_review"
    assert len(get_refund_history()) == 0


def test_human_approval_allows_execution():
    clear_mock_refund_ledger()

    result = refund_graph.invoke({
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "product_id": "P100",
        "quantity": 1,
        "reason": "damaged",
        "human_approved": True,
    })

    assert result["decision"] == "auto_approve"
    assert result["refund_status"] == "success"
    assert len(get_refund_history()) == 1


def test_duplicate_request_does_not_create_second_refund():
    clear_mock_refund_ledger()

    request = {
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "product_id": "P200",
        "quantity": 1,
        "reason": "damaged",
    }

    first = refund_graph.invoke(request)
    second = refund_graph.invoke(request)

    assert first["refund_reference"] == second["refund_reference"]
    assert len(get_refund_history()) == 1
