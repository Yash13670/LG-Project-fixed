from datetime import date
from decimal import Decimal
from app.ecommerce.models import Order, OrderStatus, RefundDecision, RefundPolicy, RefundRequest

def evaluate_refund_request(order: Order | None, request: RefundRequest,
                            today: date, policy: RefundPolicy = RefundPolicy()) -> RefundDecision:
    """Deterministic eligibility check only. It never executes a refund."""
    def deny(code: str, message: str) -> RefundDecision:
        return RefundDecision(False, request.order_id, request.product_id,
                              reason_code=code, explanation=message)

    if order is None:
        return deny("ORDER_NOT_FOUND", "No order was found for this order ID.")
    if order.customer_id != request.customer_id:
        return deny("CUSTOMER_MISMATCH", "The order does not belong to this customer.")
    if order.status == OrderStatus.CANCELLED:
        return deny("ORDER_CANCELLED", "Cancelled orders cannot use the return workflow.")
    if policy.require_delivery_for_return and order.status != OrderStatus.DELIVERED:
        return deny("NOT_DELIVERED", "The order must be delivered before a return can be requested.")
    if order.delivered_date is None:
        return deny("DELIVERY_DATE_MISSING", "Delivery date is unavailable; manual review is required.")

    matches = [i for i in order.items if i.product.product_id == request.product_id]
    if not matches:
        return deny("PRODUCT_NOT_IN_ORDER", "The requested product is not part of this order.")
    item = matches[0]
    if not item.product.returnable:
        return deny("NON_RETURNABLE_ITEM", "This product is marked as non-returnable.")
    if request.quantity <= 0:
        return deny("INVALID_QUANTITY", "Requested quantity must be greater than zero.")
    if request.quantity > item.quantity:
        return deny("QUANTITY_EXCEEDS_ORDER", "Requested quantity exceeds the quantity in the order.")

    window = item.product.return_window_days or policy.default_return_window_days
    elapsed = (today - order.delivered_date).days
    if elapsed < 0:
        return deny("INVALID_DELIVERY_DATE", "Delivery date is in the future.")
    if elapsed > window:
        return deny("RETURN_WINDOW_EXPIRED", f"The configured return window of {window} days has expired.")

    amount = (item.unit_price * request.quantity).quantize(Decimal("0.01"))
    if request.requested_amount is not None and request.requested_amount != amount:
        return deny("AMOUNT_MISMATCH", "Requested amount does not match the calculated item value.")

    return RefundDecision(
        eligible=True, order_id=request.order_id, product_id=request.product_id,
        approved_amount=amount, reason_code="ELIGIBLE_FOR_REVIEW",
        explanation="Eligible under the configured mock policy. No refund has been executed.",
        metadata={"days_since_delivery": elapsed, "return_window_days": window, "policy_mode": "mock"}
    )
