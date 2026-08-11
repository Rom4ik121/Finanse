"""Binance public ticker client for crypto spot prices."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from lib.domain.entities.money import quantize_rate

logger = logging.getLogger("finanse.infrastructure.api.binance")

DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

# Optional overrides when the Binance pair is not ``{TICKER}USDT``.
PAIR_OVERRIDES: dict[str, str] = {
    "USDT": "USDTUSDT",
}


class BinanceRateClientError(Exception):
    """Raised when the Binance ticker API call fails."""


class BinanceRateClient:
    """Async Binance client for major crypto prices in USDT ≈ USD."""

    def __init__(
        self,
        *,
        base_url: str = BINANCE_TICKER_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        pair_overrides: Optional[dict[str, str]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._pair_overrides = pair_overrides or dict(PAIR_OVERRIDES)
        self._client = client
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._owns_client = True
        return self._client

    def _pair_for(self, ticker: str) -> str:
        ticker = ticker.upper()
        return self._pair_overrides.get(ticker, f"{ticker}USDT")

    async def fetch_prices(
        self,
        symbols: Optional[list[str]] = None,
    ) -> dict[str, Decimal]:
        """Fetch USDT prices for crypto tickers.

        Uses a single ``/ticker/price`` call (all symbols), then picks the
        pairs we care about. Tickers without a Binance USDT market are skipped
        silently so CoinGecko can fill the gaps.

        Returns:
            Mapping ticker -> price in USDT as :class:`Decimal`.
        """
        wanted = [s.upper() for s in (symbols or [])]
        if not wanted:
            return {}

        client = self._ensure_client()
        try:
            response = await client.get(self._base_url)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise BinanceRateClientError("Timeout fetching Binance prices") from exc
        except httpx.HTTPError as exc:
            raise BinanceRateClientError("HTTP error fetching Binance prices") from exc

        if not isinstance(payload, list):
            raise BinanceRateClientError("Unexpected Binance payload")

        by_pair: dict[str, Decimal] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            pair = str(item.get("symbol") or "")
            raw = item.get("price")
            if not pair or raw is None:
                continue
            try:
                by_pair[pair] = Decimal(str(raw))
            except (InvalidOperation, ValueError, TypeError):
                continue

        results: dict[str, Decimal] = {}
        missing = 0
        for ticker in wanted:
            if ticker == "USDT":
                results[ticker] = Decimal("1")
                continue
            pair = self._pair_for(ticker)
            price = by_pair.get(pair)
            if price is None:
                missing += 1
                continue
            results[ticker] = quantize_rate(price, crypto=True)

        if not results:
            raise BinanceRateClientError("No Binance prices matched requested tickers")
        logger.info(
            "Fetched %d Binance prices (%d not listed on Binance)",
            len(results),
            missing,
        )
        return results


# Back-compat alias used by older wiring / tests.
DEFAULT_SYMBOLS: dict[str, str] = {
    code: (PAIR_OVERRIDES.get(code, f"{code}USDT"))
    for code in (
        "BTC",
        "ETH",
        "USDT",
        "BNB",
        "USDC",
        "XRP",
        "SOL",
        "TRX",
        "DOGE",
        "ADA",
        "AVAX",
        "DOT",
        "LINK",
        "LTC",
        "TON",
        "SHIB",
        "NEAR",
        "ATOM",
        "UNI",
        "APT",
        "ARB",
        "FIL",
        "ETC",
        "PEPE",
        "SUI",
        "POL",
        "MATIC",
        "ENA",
        "WLD",
        "ONDO",
        "JUP",
        "TAO",
        "AAVE",
        "MNT",
        "ICP",
        "HBAR",
        "XLM",
        "BCH",
        "ALGO",
        "RENDER",
        "QNT",
        "JST",
        "ZEC",
        "PAXG",
        "XAUT",
    )
}
