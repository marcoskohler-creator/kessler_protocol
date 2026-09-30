from pricing import calculate_total


def build_invoice(items):
    return {"total": calculate_total(items), "line_count": len(items)}
