"""In-memory FX conversion from a snapshot of exchange rates.

Avoids thousands of DB round-trips when converting analytics / dashboard totals.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping, Optional, Sequence

from lib.domain.entities.currency import ExchangeRate
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.money import quantize_money

_PIVOTS = ("USD", "USDT", "EUR", "UZS", "RUB", "KZT", "GBP")


class RateBook:
    """Pure-CPU converter built from ``list_rates()`` rows."""

    __slots__ = ("_direct", "_factors")

    def __init__(self, rates: Sequence[ExchangeRate] | Iterable[ExchangeRate] = ()) -> None:
        self._direct: dict[tuple[str, str], Decimal] = {}
        for rate in rates:
            base = normalize_currency_code(rate.base)
            quote = normalize_currency_code(rate.quote)
            if rate.rate and rate.rate != 0:
                self._direct[(base, quote)] = Decimal(str(rate.rate))
        self._factors: dict[tuple[str, str], Optional[Decimal]] = {}

    @classmethod
    def from_pairs(cls, pairs: Mapping[tuple[str, str], Decimal]) -> "RateBook":
        book = cls(())
        for (base, quote), rate in pairs.items():
            if rate and rate != 0:
                book._direct[
                    (normalize_currency_code(base), normalize_currency_code(quote))
                ] = Decimal(str(rate))
        return book

    def _pair_factor(self, src: str, dst: str) -> Optional[Decimal]:
        if src == dst:
            return Decimal("1")
        direct = self._direct.get((src, dst))
        if direct is not None:
            return direct
        inverse = self._direct.get((dst, src))
        if inverse is not None and inverse != 0:
            return Decimal("1") / inverse
        return None

    def factor(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Return ``dst`` units per 1 ``src``, or ``None`` if unknown."""
        src = normalize_currency_code(from_currency)
        dst = normalize_currency_code(to_currency)
        key = (src, dst)
        if key in self._factors:
            return self._factors[key]
        factor = self._pair_factor(src, dst)
        if factor is None:
            for pivot in _PIVOTS:
                if pivot in {src, dst}:
                    continue
                to_pivot = self._pair_factor(src, pivot)
                from_pivot = self._pair_factor(pivot, dst)
                if to_pivot is not None and from_pivot is not None:
                    factor = to_pivot * from_pivot
                    break
        self._factors[key] = factor
        return factor

    def convert(
        self,
        amount: Decimal | int | float | str,
        from_currency: str,
        to_currency: str,
        *,
        quantize: bool = True,
    ) -> Optional[Decimal]:
        """Convert ``amount`` or return ``None`` when no path exists."""
        raw = Decimal(str(amount))
        value = quantize_money(raw) if quantize else raw
        src = normalize_currency_code(from_currency)
        dst = normalize_currency_code(to_currency)
        if src == dst:
            return value
        factor = self.factor(src, dst)
        if factor is None:
            return None
        result = value * factor
        return quantize_money(result) if quantize else result
