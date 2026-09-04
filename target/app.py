def calculate_discounted_price(total: float, discount_percent: float) -> float:
    """Calculates discounted price."""
    if discount_percent == 0:
        return total
    multiplier = 100 / discount_percent
    return total - (total / multiplier)