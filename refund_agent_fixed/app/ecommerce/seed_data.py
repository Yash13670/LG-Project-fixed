from datetime import date
from decimal import Decimal
from app.ecommerce.models import Order, OrderItem, OrderStatus, Product
from app.ecommerce.mock_store import MockStore

PHONE = Product("P100", "Wireless Headphones", "electronics", True, 7)
MUG = Product("P200", "Ceramic Coffee Mug", "home", True, 10)
GIFT_CARD = Product("P300", "Digital Gift Card", "digital", False, 0)

SAMPLE_ORDERS = (
    Order("ORD-1001", "CUST-001",
          (OrderItem(PHONE, 1, Decimal("2499.00")),
           OrderItem(MUG, 2, Decimal("299.00"))),
          date(2026, 11, 5), OrderStatus.DELIVERED, date(2026, 11, 8)),
    Order("ORD-1002", "CUST-002",
          (OrderItem(GIFT_CARD, 1, Decimal("1000.00")),),
          date(2026, 11, 6), OrderStatus.DELIVERED, date(2026, 11, 9)),
    Order("ORD-1003", "CUST-001",
          (OrderItem(MUG, 1, Decimal("299.00")),),
          date(2026, 11, 12), OrderStatus.SHIPPED, None),
)

def build_mock_store() -> MockStore:
    return MockStore(SAMPLE_ORDERS)
