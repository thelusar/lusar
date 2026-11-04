"""LUSAR loyalty rules for eligible merchandise spend."""
from decimal import Decimal, ROUND_DOWN

# Lifetime eligible spend in AMD, followed by the discount percentage.
LOYALTY_TIERS = ((0, 0), (50_000, 3), (100_000, 5), (300_000, 7), (500_000, 10), (1_000_000, 15))
FIRST_ORDER_PERCENT = 10


def first_order_available(*, registered, promotion_active, orders):
    """A full return changes the order status from completed to cancelled."""
    return registered and promotion_active and not any(order["status"] == "completed" for order in orders)


def eligible_spend(order):
    """Use settled merchandise amounts after discounts, excluding delivery."""
    if order["status"] != "completed" or not order["paid"]:
        return Decimal(0)
    merchandise = Decimal(str(order["paid_merchandise"]))
    refunded = Decimal(str(order.get("refunded_merchandise", 0)))
    if not merchandise.is_finite() or not refunded.is_finite() or not 0 <= refunded <= merchandise:
        raise ValueError("Некорректная сумма оплаты или возврата.")
    return merchandise - refunded


def eligible_spend_from_saved_order(status, order):
    """Read eligibility directly from a saved manager order and its returns."""
    payment = order.get("payment")
    if status != "completed" or not payment:
        return Decimal(0)
    remaining = order.get("remainingAmount", order)["total"]
    return eligible_spend({
        "status": status,
        "paid": True,
        "paid_merchandise": payment["amount"],
        "refunded_merchandise": Decimal(str(payment["amount"])) - Decimal(str(remaining)),
    })


def loyalty_progress(orders, tiers=LOYALTY_TIERS):
    """Calculate current discount and progress from the customer's orders."""
    spent = int(sum((eligible_spend(order) for order in orders), Decimal(0)).to_integral_value(rounding=ROUND_DOWN))
    current = max(index for index, (threshold, _) in enumerate(tiers) if threshold <= spent)
    next_tier = tiers[current + 1] if current + 1 < len(tiers) else None
    return {
        "eligibleSpend": spent,
        "discountPercent": tiers[current][1],
        "nextDiscountPercent": next_tier[1] if next_tier else None,
        "remainingToNext": next_tier[0] - spent if next_tier else None,
    }
