"""Fiat exchange-rate client (open.er-api.com)."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

from lib.domain.entities.money import quantize_rate

logger = logging.getLogger("finanse.infrastructure.api.exchange_rate")

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
OPEN_ER_API_URL = "https://open.er-api.com/v6/latest/{base}"


class ExchangeRateClientError(Exception):
    """Raised when the exchange-rate API call fails."""


class ExchangeRateClient:
    """Async client for open ExchangeRate-API (no key required).

    Endpoint: ``https://open.er-api.com/v6/latest/{base}``
    """

    def __init__(
        self,
        *,
        base_url_template: str = OPEN_ER_API_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url_template = base_url_template
        self._timeout = timeout
        self._api_key = api_key
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "ExchangeRateClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._owns_client = True
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._owns_client = True
        return self._client

    async def fetch_latest(self, base: str = "USD") -> dict[str, Decimal]:
        """Fetch latest rates relative to ``base``.

        Returns:
            Mapping of quote currency code -> rate as :class:`Decimal`.

        Raises:
            ExchangeRateClientError: On network, HTTP, or payload errors.
        """
        base_code = base.strip().upper()
        url = self._base_url_template.format(base=base_code)
        params: dict[str, Any] = {}
        if self._api_key:
            # freecurrencyapi.com style key support when a custom template is used
            params["apikey"] = self._api_key

        client = self._ensure_client()
        try:
            response = await client.get(url, params=params or None)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            logger.warning("Exchange rate request timed out for base=%s", base_code)
            raise ExchangeRateClientError(f"Timeout fetching rates for {base_code}") from exc
        except httpx.HTTPError as exc:
            logger.warning("Exchange rate HTTP error for base=%s: %s", base_code, exc)
            raise ExchangeRateClientError(f"HTTP error fetching rates for {base_code}") from exc
        except ValueError as exc:
            logger.exception("Invalid JSON from exchange rate API for base=%s", base_code)
            raise ExchangeRateClientError("Invalid JSON from exchange rate API") from exc

        rates_raw = self._extract_rates(payload)
        if not rates_raw:
            logger.error("No rates in exchange API response for base=%s: %s", base_code, payload)
            raise ExchangeRateClientError("Empty rates payload")

        result: dict[str, Decimal] = {}
        for code, value in rates_raw.items():
            try:
                result[str(code).upper()] = quantize_rate(value, crypto=False)
            except (InvalidOperation, ValueError, TypeError):
                logger.warning("Skipping invalid rate %s=%r", code, value)
        logger.info("Fetched %s fiat rates for base=%s", len(result), base_code)
        return result

    async def get_rate(self, base: str, quote: str) -> Decimal:
        """Return ``1 base = rate quote``."""
        quote_code = quote.strip().upper()
        rates = await self.fetch_latest(base)
        if quote_code not in rates:
            raise ExchangeRateClientError(f"Quote {quote_code} not found for base {base}")
        return rates[quote_code]

    @staticmethod
    def _extract_rates(payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize open.er-api / freecurrencyapi response shapes."""
        if "rates" in payload and isinstance(payload["rates"], dict):
            return payload["rates"]
        data = payload.get("data")
        if isinstance(data, dict):
            # freecurrencyapi: data -> {USD: {value: 1.0}, ...} or {USD: 1.0}
            normalized: dict[str, Any] = {}
            for code, entry in data.items():
                if isinstance(entry, dict) and "value" in entry:
                    normalized[code] = entry["value"]
                else:
                    normalized[code] = entry
            return normalized
        return {}
