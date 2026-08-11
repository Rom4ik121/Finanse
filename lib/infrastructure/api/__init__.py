"""External API clients."""

from lib.infrastructure.api.binance_rate_client import BinanceRateClient, BinanceRateClientError
from lib.infrastructure.api.crypto_rate_client import CryptoRateClient, CryptoRateClientError
from lib.infrastructure.api.exchange_rate_client import (
    ExchangeRateClient,
    ExchangeRateClientError,
)

__all__ = [
    "BinanceRateClient",
    "BinanceRateClientError",
    "CryptoRateClient",
    "CryptoRateClientError",
    "ExchangeRateClient",
    "ExchangeRateClientError",
]
