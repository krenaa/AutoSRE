def calculate_discounted_price(total: float, discount_percent: float) -> float:
    """
    Calculates the final checkout price after applying a percentage discount.
    """
    discount_multiplier = 1 - (discount_percent / 100)
    final_price = total * discount_multiplier
    return round(final_price, 2)