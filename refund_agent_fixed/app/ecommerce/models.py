from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

class OrderStatus(str, Enum):
    PLACED = "placed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class RefundReason(str, Enum):
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    MISSING_ITEM = "missing_item"
    NOT_AS_DESCRIBED = "not_as_described"
    LATE_DELIVERY = "late_delivery"
    OTHER = "other"

@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    category: str
    returnable: bool = True
    return_window_days: int = 7

@dataclass(frozen=True)
class OrderItem:
    product: Product
    quantity: int
    unit_price: Decimal
    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    items: tuple[OrderItem, ...]
    order_date: date
    status: OrderStatus
    delivered_date: Optional[date] = None
    @property
    def total_amount(self) -> Decimal:
        return sum((i.line_total for i in self.items), Decimal("0.00"))

@dataclass(frozen=True)
class RefundRequest:
    request_id: str
    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    reason: RefundReason
    requested_amount: Optional[Decimal] = None
    evidence_file: Optional[str] = None

@dataclass(frozen=True)
class RefundPolicy:
    default_return_window_days: int = 7
    require_delivery_for_return: bool = True
    allow_partial_quantity: bool = True

@dataclass
class RefundDecision:
    eligible: bool
    order_id: str
    product_id: str
    approved_amount: Decimal = Decimal("0.00")
    reason_code: str = ""
    explanation: str = ""
    requires_human_review: bool = False
    metadata: dict = field(default_factory=dict)
