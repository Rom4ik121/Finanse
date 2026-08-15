"""Crypto price client (CoinGecko simple price API)."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from lib.domain.entities.money import quantize_rate

logger = logging.getLogger("finanse.infrastructure.api.crypto_rate")

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# App ticker -> CoinGecko id
DEFAULT_COINS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "USDC": "usd-coin",
    "XRP": "ripple",
    "SOL": "solana",
    "TRX": "tron",
    "FIGR_HELOC": "figure-heloc",
    "HYPE": "hyperliquid",
    "DOGE": "dogecoin",
    "USDS": "usds",
    "RAIN": "rain",
    "LEO": "leo-token",
    "ZEC": "zcash",
    "XMR": "monero",
    "ADA": "cardano",
    "WBT": "whitebit",
    "LINK": "chainlink",
    "XLM": "stellar",
    "DAI": "dai",
    "BCH": "bitcoin-cash",
    "USD1": "usd1-wlfi",
    "USDE": "ethena-usde",
    "CC": "canton-network",
    "LTC": "litecoin",
    "USDG": "global-dollar",
    "USYC": "hashnote-usyc",
    "HBAR": "hedera-hashgraph",
    "SUI": "sui",
    "PYUSD": "paypal-usd",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "BUIDL": "blackrock-usd-institutional-digital-liquidity-fund",
    "XAUT": "tether-gold",
    "UNI": "uniswap",
    "CRO": "crypto-com-chain",
    "USDY": "ondo-us-dollar-yield",
    "NEAR": "near",
    "OKB": "okb",
    "TAO": "bittensor",
    "PAXG": "pax-gold",
    "WLFI": "world-liberty-financial",
    "ONDO": "ondo-finance",
    "HTX": "htx-dao",
    "ASTER": "aster-2",
    "USDD": "usdd",
    "RLUSD": "ripple-usd",
    "M": "memecore",
    "MNT": "mantle",
    "AAVE": "aave",
    "DOT": "polkadot",
    "USDF": "falcon-finance",
    "BFUSD": "bfusd",
    "ICP": "internet-computer",
    "MORPHO": "morpho",
    "SKY": "sky",
    "WLD": "worldcoin-wld",
    "U": "united-stables",
    "PEPE": "pepe",
    "USDGO": "usdgo",
    "BGB": "bitget-token",
    "PUMP": "pump-fun",
    "EURSAFO": "spiko-amundi-overnight-swap-fund-eur",
    "ETC": "ethereum-classic",
    "PI": "pi-network",
    "BCAP": "blockchain-capital",
    "USTB": "superstate-short-duration-us-government-securities-fund-ustb",
    "EUTBL": "eutbl",
    "KCS": "kucoin-shares",
    "JTRSY": "janus-henderson-anemoy-treasury-fund",
    "ENA": "ethena",
    "QNT": "quant-network",
    "JST": "just",
    "POL": "polygon-ecosystem-token",
    "STABLE": "stable-2",
    "ATOM": "cosmos",
    "ALGO": "algorand",
    "BDX": "beldex",
    "NEXO": "nexo",
    "KAS": "kaspa",
    "GT": "gatechain-token",
    "GHO": "gho",
    "JAAA": "janus-henderson-anemoy-aaa-clo-fund",
    "RENDER": "render-token",
    "YLDS": "ylds",
    "BEAT": "audiera",
    "JUP": "jupiter-exchange-solana",
    "LIT": "lighter",
    "FIL": "filecoin",
    "VVV": "venice-token",
    "USD0": "usual-usd",
    "XDC": "xdce-crowd-sale",
    "ARB": "arbitrum",
    "FLR": "flare-networks",
    "BTW": "bitway",
    "USX": "usx",
    "APT": "aptos",
    "MATIC": "matic-network",
    "TON": "the-open-network",
}


class CryptoRateClientError(Exception):
    """Raised when the crypto price API call fails."""


class CryptoRateClient:
    """Async CoinGecko client for major crypto spot prices."""

    def __init__(
        self,
        *,
        base_url: str = COINGECKO_SIMPLE_PRICE_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        vs_currency: str = "usd",
        coin_map: Optional[dict[str, str]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._vs_currency = vs_currency.lower()
        self._coin_map = coin_map or dict(DEFAULT_COINS)
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "CryptoRateClient":
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

    async def fetch_prices(
        self,
        symbols: Optional[list[str]] = None,
        *,
        vs_currency: Optional[str] = None,
    ) -> dict[str, Decimal]:
        """Fetch prices for crypto tickers.

        Args:
            symbols: Tickers such as ``BTC``, ``ETH``. Defaults to the built-in set.
            vs_currency: Quote currency for CoinGecko (default ``usd``).

        Returns:
            Mapping of ticker -> price in ``vs_currency`` as :class:`Decimal`.
        """
        tickers = [s.upper() for s in (symbols or list(self._coin_map.keys()))]
        ids: list[str] = []
        id_to_ticker: dict[str, str] = {}
        for ticker in tickers:
            coin_id = self._coin_map.get(ticker)
            if coin_id is None:
                logger.warning("Unknown crypto ticker skipped: %s", ticker)
                continue
            ids.append(coin_id)
            id_to_ticker[coin_id] = ticker

        if not ids:
            raise CryptoRateClientError("No valid crypto symbols to fetch")

        vs = (vs_currency or self._vs_currency).lower()
        params = {
            "ids": ",".join(ids),
            "vs_currencies": vs,
        }

        client = self._ensure_client()
        try:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            logger.warning("CoinGecko request timed out")
            raise CryptoRateClientError("Timeout fetching crypto prices") from exc
        except httpx.HTTPError as exc:
            logger.warning("CoinGecko HTTP error: %s", exc)
            raise CryptoRateClientError("HTTP error fetching crypto prices") from exc
        except ValueError as exc:
            logger.warning("Invalid JSON from CoinGecko: %s", exc)
            raise CryptoRateClientError("Invalid JSON from CoinGecko") from exc

        if not isinstance(payload, dict):
            raise CryptoRateClientError("Unexpected CoinGecko payload")

        result: dict[str, Decimal] = {}
        for coin_id, ticker in id_to_ticker.items():
            entry = payload.get(coin_id)
            if not isinstance(entry, dict) or vs not in entry:
                logger.warning("Missing price for %s (%s)", ticker, coin_id)
                continue
            try:
                result[ticker] = quantize_rate(entry[vs], crypto=True)
            except (InvalidOperation, ValueError, TypeError):
                logger.warning("Invalid price for %s: %r", ticker, entry.get(vs))

        logger.info("Fetched %s crypto prices vs %s", len(result), vs.upper())
        return result

    async def get_price(self, symbol: str, *, vs_currency: Optional[str] = None) -> Decimal:
        """Return a single ticker price."""
        prices = await self.fetch_prices([symbol], vs_currency=vs_currency)
        ticker = symbol.upper()
        if ticker not in prices:
            raise CryptoRateClientError(f"Price not available for {ticker}")
        return prices[ticker]
