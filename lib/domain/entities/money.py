"""Money and rate quantization helpers."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from lib.core.config import CRYPTO_RATE_QUANTIZE, FIAT_RATE_QUANTIZE, MONEY_QUANTIZE

_MONEY_Q = Decimal(MONEY_QUANTIZE)
_FIAT_RATE_Q = Decimal(FIAT_RATE_QUANTIZE)
_CRYPTO_Q = Decimal(CRYPTO_RATE_QUANTIZE)


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    """Quantize a monetary amount to 2 decimal places (HALF_UP)."""
    return Decimal(str(value)).quantize(_MONEY_Q, rounding=ROUND_HALF_UP)


def quantize_rate(value: Decimal | int | float | str, *, crypto: bool = False) -> Decimal:
    """Quantize an exchange rate to high precision.

    Fiat and crypto both use 8 decimal places so weak currencies (UZS, etc.)
    are not rounded to 0.00.
    """
    q = _CRYPTO_Q if crypto else _FIAT_RATE_Q
    return Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP)
