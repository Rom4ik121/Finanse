"""Composite FX + crypto rate provider for domain use cases."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from lib.domain.entities.currency import ExchangeRate
from lib.domain.entities.money import quantize_rate
from lib.infrastructure.api.binance_rate_client import BinanceRateClient
from lib.infrastructure.api.crypto_rate_client import CryptoRateClient, DEFAULT_COINS
from lib.infrastructure.api.exchange_rate_client import ExchangeRateClient

logger = logging.getLogger("finanse.infrastructure.exchange_rate_provider")


class HttpExchangeRateProvider:
    """Fetches fiat (open.er-api.com) and crypto (Binance → CoinGecko fallback).

    Implements the ``ExchangeRateProvider`` protocol expected by
    :class:`~lib.domain.use_cases.currencies.UpdateExchangeRatesUseCase`.

    Conversion path: every currency is anchored to USD, then
    ``rate(base→quote) = usd_per_base / usd_per_quote``.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        fiat_client: Optional[ExchangeRateClient] = None,
        crypto_client: Optional[CryptoRateClient] = None,
        binance_client: Optional[BinanceRateClient] = None,
    ) -> None:
        self._fiat = fiat_client or ExchangeRateClient(api_key=api_key)
        self._crypto = crypto_client or CryptoRateClient()
        self._binance = binance_client or BinanceRateClient()
        self._crypto_codes = set(DEFAULT_COINS.keys())

    async def _fetch_crypto_usd(self) -> dict[str, Decimal]:
        """Prefer Binance for listed pairs; fill gaps via CoinGecko."""
        prices: dict[str, Decimal] = {}
        codes = list(self._crypto_codes)
        try:
            prices.update(await self._binance.fetch_prices(codes))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Binance crypto fetch failed; trying CoinGecko: %s", exc)

        missing = [c for c in codes if c not in prices]
        if missing:
            try:
                # CoinGecko simple/price accepts many ids; chunk to stay safe.
                chunk_size = 50
                for i in range(0, len(missing), chunk_size):
                    chunk = missing[i : i + chunk_size]
                    prices.update(
                        await self._crypto.fetch_prices(chunk, vs_currency="usd")
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("CoinGecko crypto fetch failed: %s", exc)
        return prices

    async def fetch_rates(
        self,
        base: str,
        quotes: Sequence[str],
    ) -> Sequence[ExchangeRate]:
        """Return rates for ``base`` against each requested quote."""
        base_code = base.strip().upper()
        quote_codes = sorted({q.strip().upper() for q in quotes if q and q.strip()})
        now = datetime.now(timezone.utc)

        usd_per_unit: dict[str, Decimal] = {"USD": Decimal("1")}

        try:
            usd_book = await self._fiat.fetch_latest("USD")
            for code, units_per_usd in usd_book.items():
                if units_per_usd and units_per_usd != 0:
                    usd_per_unit[code.upper()] = Decimal("1") / units_per_usd
        except Exception as exc:  # noqa: BLE001
            # Keep last persisted rates; timeouts are expected on flaky networks.
            logger.warning("Fiat USD book fetch failed: %s", exc)

        needed_crypto = {
            c for c in ([base_code] + quote_codes) if c in self._crypto_codes
        }
        if needed_crypto or any(c in self._crypto_codes for c in usd_per_unit):
            crypto_usd = await self._fetch_crypto_usd()
            for code, price in crypto_usd.items():
                if price and price != 0:
                    usd_per_unit[code.upper()] = price

        base_usd = usd_per_unit.get(base_code)
        if base_usd is None or base_usd == 0:
            logger.warning("No USD anchor for base=%s", base_code)
            return []

        results: list[ExchangeRate] = []
        for quote in quote_codes:
            if quote == base_code:
                results.append(
                    ExchangeRate(
                        base=base_code,
                        quote=quote,
                        rate=Decimal("1"),
                        updated_at=now,
                    )
                )
                continue
            quote_usd = usd_per_unit.get(quote)
            if quote_usd is None or quote_usd == 0:
                continue
            rate = base_usd / quote_usd
            if rate <= 0:
                continue
            is_crypto = quote in self._crypto_codes or base_code in self._crypto_codes
            quantized = quantize_rate(rate, crypto=is_crypto)
            # Skip pairs that underflow to 0 after quantization (e.g. UZS→BTC).
            if quantized <= 0:
                logger.debug(
                    "Skipping near-zero rate %s→%s (%s)",
                    base_code,
                    quote,
                    rate,
                )
                continue
            results.append(
                ExchangeRate(
                    base=base_code,
                    quote=quote,
                    rate=quantized,
                    updated_at=now,
                )
            )

        # Also persist USD-anchored rows so pairs like BTC/USD convert even
        # when the app base is a weak fiat (UZS) that underflows vs crypto.
        if base_code != "USD":
            seen = {(r.base, r.quote) for r in results}
            for code, usd_price in usd_per_unit.items():
                if code == "USD" or usd_price is None or usd_price <= 0:
                    continue
                is_crypto = code in self._crypto_codes
                usd_to_code = Decimal("1") / usd_price
                code_to_usd = usd_price
                for pair_base, pair_quote, pair_rate in (
                    ("USD", code, usd_to_code),
                    (code, "USD", code_to_usd),
                ):
                    key = (pair_base, pair_quote)
                    if key in seen:
                        continue
                    quantized = quantize_rate(pair_rate, crypto=is_crypto)
                    if quantized <= 0:
                        continue
                    seen.add(key)
                    results.append(
                        ExchangeRate(
                            base=pair_base,
                            quote=pair_quote,
                            rate=quantized,
                            updated_at=now,
                        )
                    )
        return results
