"""Currency and exchange-rate use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Protocol, Sequence

from lib.domain.entities.currency import Currency, ExchangeRate
from lib.domain.entities.money import quantize_money, quantize_rate
from lib.domain.repositories.currency_repository import CurrencyRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExchangeRateProvider(Protocol):
    """Port for an external FX / crypto rate source."""

    async def fetch_rates(
        self,
        base: str,
        quotes: Sequence[str],
    ) -> Sequence[ExchangeRate]:
        """Fetch rates for ``base`` against each quote code."""


class UpdateExchangeRatesUseCase:
    """Refresh stored exchange rates from an external provider."""

    def __init__(
        self,
        currencies: CurrencyRepository,
        provider: Optional[ExchangeRateProvider] = None,
    ) -> None:
        self._currencies = currencies
        self._provider = provider

    async def execute(
        self,
        *,
        base: str = "RUB",
        quotes: Optional[Sequence[str]] = None,
        rates: Optional[Sequence[ExchangeRate]] = None,
    ) -> list[ExchangeRate]:
        """Update rates either from ``rates`` payload or via ``provider``.

        Args:
            base: Base currency code.
            quotes: Quote codes to request when using the provider.
            rates: Precomputed rates to upsert (skips provider).

        Returns:
            Persisted exchange rates.
        """
        base = base.upper()
        if rates is not None:
            normalized = [
                r.model_copy(
                    update={
                        "base": r.base.upper(),
                        "quote": r.quote.upper(),
                        "rate": quantize_rate(r.rate, crypto=True),
                        "updated_at": r.updated_at or _utc_now(),
                    }
                )
                for r in rates
            ]
            return await self._currencies.upsert_rates(normalized)

        if self._provider is None:
            raise RuntimeError(
                "No exchange-rate provider configured and no rates supplied"
            )

        if not quotes:
            known = await self._currencies.list_currencies(include_crypto=True)
            quotes = [c.code for c in known if c.code != base]

        fetched = await self._provider.fetch_rates(base, quotes)
        normalized = [
            r.model_copy(
                update={
                    "rate": quantize_rate(r.rate, crypto=True),
                    "updated_at": _utc_now(),
                }
            )
            for r in fetched
        ]
        return await self._currencies.upsert_rates(normalized)


class ConvertCurrencyUseCase:
    """Convert an amount between currencies using stored rates."""

    def __init__(self, currencies: CurrencyRepository) -> None:
        self._currencies = currencies

    async def execute(
        self,
        amount: Decimal,
        *,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Convert ``amount`` from ``from_currency`` to ``to_currency``.

        Supports direct rates and inverse rates. Result is quantized to
        2 decimal places for fiat-style money amounts.
        """
        amount = quantize_money(amount)
        src = from_currency.upper()
        dst = to_currency.upper()
        if src == dst:
            return amount

        rate = await self._currencies.get_rate(src, dst)
        if rate is not None:
            return quantize_money(amount * rate.rate)

        inverse = await self._currencies.get_rate(dst, src)
        if inverse is not None and inverse.rate != 0:
            return quantize_money(amount / inverse.rate)

        raise ValueError(f"No exchange rate found for {src}/{dst}")


class ListCurrenciesUseCase:
    """List known currencies."""

    def __init__(self, currencies: CurrencyRepository) -> None:
        self._currencies = currencies

    async def execute(self, *, include_crypto: bool = True) -> list[Currency]:
        """Return currency definitions."""
        return await self._currencies.list_currencies(include_crypto=include_crypto)
