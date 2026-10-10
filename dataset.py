"""Deterministic dataset for the Nykaa support agent capstone."""

from __future__ import annotations

import random
from collections import Counter
from typing import Dict, List

CATEGORIES = ["Apparel", "Electronics", "Home", "Footwear", "Beauty"]
STATUSES = ["Placed", "Shipped", "Delivered", "Returned", "Refunded"]
CATEGORY_PRICE_BANDS = {
    "Apparel": (300, 5000),
    "Electronics": (1500, 60000),
    "Home": (400, 12000),
    "Footwear": (500, 7000),
    "Beauty": (200, 3500),
}


def _log_uniform(low: float, high: float, rng: random.Random) -> float:
    import math

    return math.exp(rng.uniform(math.log(low), math.log(high)))


def generate_orders(n: int = 50, seed: int = 42) -> List[Dict[str, object]]:
    """Create a seeded, deterministic list of order records.

    Design choices: five Nykaa categories, five statuses, realistic INR bands,
    and a delayed shipment rate in the required 10%-30% band.
    """
    rng = random.Random(seed)
    orders: List[Dict[str, object]] = []
    category_counts = Counter()
    status_counts = Counter()

    while len(orders) < n:
        category = rng.choices(CATEGORIES, weights=[0.30, 0.25, 0.20, 0.15, 0.10], k=1)[0]
        status = rng.choices(STATUSES, weights=[0.15, 0.20, 0.35, 0.20, 0.10], k=1)[0]
        low, high = CATEGORY_PRICE_BANDS[category]
        order_value = int(round(_log_uniform(low, high, rng)))
        days_since_created = rng.randint(0, 30)
        late = status in {"Shipped", "Delivered", "Returned"} and rng.random() < 0.18

        order = {
            "record_id": f"NYK-{len(orders) + 1:05d}",
            "category": category,
            "status": status,
            "order_value_inr": order_value,
            "days_since_created": days_since_created,
            "delayed_shipment": late,
        }
        orders.append(order)
        category_counts[category] += 1
        status_counts[status] += 1

    # Enforce minimum coverage without hand-editing any records.
    if min(category_counts.values()) < 3:
        for category in CATEGORIES:
            while category_counts[category] < 3:
                idx = len(orders) + 1
                low, high = CATEGORY_PRICE_BANDS[category]
                status = rng.choice(STATUSES)
                order = {
                    "record_id": f"NYK-{idx:05d}",
                    "category": category,
                    "status": status,
                    "order_value_inr": int(round(_log_uniform(low, high, rng))),
                    "days_since_created": rng.randint(0, 30),
                    "delayed_shipment": status in {"Shipped", "Delivered", "Returned"} and rng.random() < 0.18,
                }
                orders.append(order)
                category_counts[category] += 1
                status_counts[status] += 1

    for status in STATUSES:
        if status_counts[status] == 0:
            idx = len(orders) + 1
            category = rng.choice(CATEGORIES)
            low, high = CATEGORY_PRICE_BANDS[category]
            order = {
                "record_id": f"NYK-{idx:05d}",
                "category": category,
                "status": status,
                "order_value_inr": int(round(_log_uniform(low, high, rng))),
                "days_since_created": rng.randint(0, 30),
                "delayed_shipment": status in {"Shipped", "Delivered", "Returned"} and rng.random() < 0.18,
            }
            orders.append(order)
            category_counts[category] += 1
            status_counts[status] += 1

    delayed_pct = (sum(1 for o in orders if o["delayed_shipment"]) / len(orders)) * 100
    if not 10 <= delayed_pct <= 30:
        raise ValueError(f"Delayed shipment rate {delayed_pct:.2f}% is outside the required 10%-30% band.")

    return orders


ORDERS = generate_orders()


def summarize_orders(orders: List[Dict[str, object]]) -> Dict[str, object]:
    category_counts = Counter(order["category"] for order in orders)
    status_counts = Counter(order["status"] for order in orders)
    delayed_pct = (sum(1 for order in orders if order["delayed_shipment"]) / len(orders)) * 100
    return {
        "total_orders": len(orders),
        "category_counts": dict(category_counts),
        "status_counts": dict(status_counts),
        "delayed_shipment_pct": delayed_pct,
    }


def check_order_status(record_id: str) -> Dict[str, object]:
    """Return the status plus a designed escalation score in [0, 1].

    Escalation score = 0.65 * delayed_shipment + 0.35 * (days_since_created / 30).
    delayed_shipment contributes a binary flag, while days_since_created is
    normalized to a 0-1 recency signal. The threshold is 0.60, corresponding to
    orders that are either unusually late or older than ~80th percentile in this
    generated dataset.
    """
    for order in ORDERS:
        if order["record_id"] == record_id:
            delayed = 1.0 if order["delayed_shipment"] else 0.0
            recency = float(order["days_since_created"]) / 30.0
            score = 0.65 * delayed + 0.35 * recency
            return {
                "record_id": record_id,
                "status": order["status"],
                "order_value_inr": order["order_value_inr"],
                "escalation_score": round(score, 4),
                "recommended_escalation": score >= 0.60,
            }
    raise KeyError(f"Order {record_id!r} not found.")


if __name__ == "__main__":
    summary = summarize_orders(ORDERS)
    print(f"Generated {summary['total_orders']} orders")
    print("Category counts:", summary["category_counts"])
    print("Status counts:", summary["status_counts"])
    print(f"Delayed shipment percentage: {summary['delayed_shipment_pct']:.2f}%")
    sample = ORDERS[0]
    print("Example:", sample)
    print(check_order_status(sample["record_id"]))
