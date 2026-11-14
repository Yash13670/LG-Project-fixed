from app.ecommerce.graph.workflow import refund_graph


def test_low_risk_refund():
    result = refund_graph.invoke({
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "product_id": "P200",
        "quantity": 1,
        "reason": "damaged",
        "description": "Product arrived damaged",
    })

    assert result["order_verified"] is True
    assert result["eligible"] is True
    assert result["decision"] == "auto_approve"
    assert result["refund_amount"] == 299


def test_undelivered_order():
    result = refund_graph.invoke({
        "customer_id": "CUST-001",
        "order_id": "ORD-1003",
        "product_id": "P200",
        "quantity": 1,
        "reason": "not_received",
    })

    assert result["eligible"] is False
    assert result["decision"] == "rejected"


def test_wrong_customer():
    result = refund_graph.invoke({
        "customer_id": "CUST-002",
        "order_id": "ORD-1001",
        "product_id": "P200",
        "quantity": 1,
        "reason": "damaged",
    })

    assert result["order_verified"] is False
    assert result["decision"] == "rejected"
