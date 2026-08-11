"""Money quantization helpers."""

from __future__ import annotations

from decimal import Decimal

from lib.domain.entities.money import quantize_money, quantize_rate


def test_quantize_money_half_up() -> None:
    assert quantize_money("1.225") == Decimal("1.23")
    assert quantize_money("1.224") == Decimal("1.22")
    assert quantize_money(100) == Decimal("100.00")


def test_quantize_rate_keeps_small_fiat() -> None:
    rate = quantize_rate("0.000000123456")
    assert rate > 0
    assert quantize_rate("1.5") == Decimal("1.50000000000000")


def test_quantize_rate_crypto_flag() -> None:
    assert quantize_rate("0.00001", crypto=True) > 0
