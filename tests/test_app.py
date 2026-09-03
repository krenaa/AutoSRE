import pytest
from target.app import calculate_discounted_price

def test_regular_discount():
    assert calculate_discounted_price(100.0, 10.0) == 90.0

def test_zero_discount():
    assert calculate_discounted_price(100.0, 0.0) == 100.0