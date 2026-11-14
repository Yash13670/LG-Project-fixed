from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.database import get_connection


def execute_mock_refund(
    idempotency_key: str,
    order_id: str,
    customer_id: str,
    amount: float,
    reason: str,
):
    """Persist a simulated refund exactly once in the existing SQLite DB."""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ecommerce_refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT NOT NULL UNIQUE,
                refund_reference TEXT NOT NULL UNIQUE,
                order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                reason TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        reference = f"MOCK-REF-{uuid4().hex[:12].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        formatted_amount = str(
            Decimal(str(amount)).quantize(Decimal("0.01"))
        )

        conn.execute("""
            INSERT OR IGNORE INTO ecommerce_refunds (
                idempotency_key, refund_reference, order_id,
                customer_id, amount, reason, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idempotency_key, reference, order_id,
            customer_id, formatted_amount, reason,
            "success", created_at
        ))

        row = conn.execute("""
            SELECT * FROM ecommerce_refunds
            WHERE idempotency_key = ?
        """, (idempotency_key,)).fetchone()

        record = dict(row)
        record["duplicate"] = record["refund_reference"] != reference
        return record


def get_refund_history():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ecommerce_refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT NOT NULL UNIQUE,
                refund_reference TEXT NOT NULL UNIQUE,
                order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                reason TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        rows = conn.execute("""
            SELECT * FROM ecommerce_refunds ORDER BY id DESC
        """).fetchall()
        return [dict(row) for row in rows]


def clear_mock_refund_ledger():
    """Test helper. Deletes only the E-commerce mock refund ledger."""
    with get_connection() as conn:
        conn.execute("DELETE FROM ecommerce_refunds")
