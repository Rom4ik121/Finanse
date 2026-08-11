"""Abstract currency / exchange-rate repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from lib.domain.entities.currency import Currency, ExchangeRate


class CurrencyRepository(ABC):
    """Persistence port for currencies and exchange rates."""

    @abstractmethod
    async def upsert_currency(self, currency: Currency) -> Currency:
        """Insert or update a currency definition."""

    @abstractmethod
    async def get_currency(self, code: str) -> Optional[Currency]:
        """Fetch a currency by code."""

    @abstractmethod
    async def list_currencies(self, *, include_crypto: bool = True) -> list[Currency]:
        """List known currencies."""

    @abstractmethod
    async def upsert_rate(self, rate: ExchangeRate) -> ExchangeRate:
        """Insert or update an exchange rate for a base/quote pair."""

    @abstractmethod
    async def get_rate(self, base: str, quote: str) -> Optional[ExchangeRate]:
        """Fetch the latest stored rate for ``base`` → ``quote``."""

    @abstractmethod
    async def list_rates(self, *, base: Optional[str] = None) -> list[ExchangeRate]:
        """List stored rates, optionally filtered by base currency."""

    @abstractmethod
    async def upsert_rates(self, rates: Sequence[ExchangeRate]) -> list[ExchangeRate]:
        """Bulk insert or update exchange rates."""

    async def list_all(self, *, crypto_only: Optional[bool] = None) -> list[Currency]:
        """Compatibility helper mapping to :meth:`list_currencies`."""
        if crypto_only is True:
            currencies = await self.list_currencies(include_crypto=True)
            return [c for c in currencies if c.is_crypto]
        if crypto_only is False:
            return await self.list_currencies(include_crypto=False)
        return await self.list_currencies(include_crypto=True)

    async def get_by_id(self, code: str) -> Optional[Currency]:
        """Compatibility helper — same as :meth:`get_currency`."""
        return await self.get_currency(code)
