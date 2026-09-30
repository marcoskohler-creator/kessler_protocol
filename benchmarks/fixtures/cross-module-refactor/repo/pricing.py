def calculate_total(items):
    """items: list of {"price": float, "qty": int}. Returns the order total."""
    return sum(i["price"] * i["qty"] for i in items)
