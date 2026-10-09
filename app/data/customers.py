from __future__ import annotations

from typing import Any

from app.data.seed import generate_synthetic_customers

# Dictionary of all 100 deterministic synthetic customers keyed by customer_id.
# Preserves baseline C101, C102, C103 fixtures for backwards compatibility with UI and tests.
customers: dict[str, dict[str, Any]] = {
    rec["customer_id"]: rec for rec in generate_synthetic_customers(100)
}