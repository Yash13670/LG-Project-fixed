from datetime import date
from decimal import Decimal
from app.ecommerce.models import RefundReason, RefundRequest
from app.ecommerce.refund_policy import evaluate_refund_request
from app.ecommerce.seed_data import build_mock_store

def req(**kwargs):
    data = dict(request_id="REQ-1", order_id="ORD-1001", customer_id="CUST-001",
                product_id="P100", quantity=1, reason=RefundReason.DAMAGED,
                requested_amount=Decimal("2499.00"))
    data.update(kwargs)
    return RefundRequest(**data)

def test_eligible_request_calculates_amount():
    store = build_mock_store()
    result = evaluate_refund_request(store.get_order("ORD-1001"), req(), date(2026, 11, 14))
    assert result.eligible
    assert result.approved_amount == Decimal("2499.00")
    assert "No refund has been executed" in result.explanation

def test_non_returnable_item_is_rejected():
    store = build_mock_store()
    request = req(order_id="ORD-1002", customer_id="CUST-002",
                  product_id="P300", requested_amount=Decimal("1000.00"))
    result = evaluate_refund_request(store.get_order("ORD-1002"), request, date(2026, 11, 14))
    assert result.reason_code == "NON_RETURNABLE_ITEM"

def test_customer_mismatch_is_rejected():
    store = build_mock_store()
    result = evaluate_refund_request(store.get_order("ORD-1001"),
                                     req(customer_id="CUST-999"), date(2026, 11, 14))
    assert result.reason_code == "CUSTOMER_MISMATCH"

def test_undelivered_order_is_rejected():
    store = build_mock_store()
    request = req(order_id="ORD-1003", product_id="P200",
                  requested_amount=Decimal("299.00"))
    result = evaluate_refund_request(store.get_order("ORD-1003"), request, date(2026, 11, 14))
    assert result.reason_code == "NOT_DELIVERED"
