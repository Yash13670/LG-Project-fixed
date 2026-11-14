from typing import Optional
from app.ecommerce.models import Order

class MockStore:
    """In-memory order repository; later replaceable by a merchant API adapter."""
    def __init__(self, orders: tuple[Order, ...] = ()):
        self._orders = {order.order_id: order for order in orders}

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def get_customer_orders(self, customer_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def add_order(self, order: Order) -> None:
        self._orders[order.order_id] = order
