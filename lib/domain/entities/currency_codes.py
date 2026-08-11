"""Normalize user-entered currency aliases to ISO-like codes."""

from __future__ import annotations

# Common aliases / symbols people type instead of ISO codes.
_ALIASES: dict[str, str] = {
    "SOM": "UZS",
    "SO'M": "UZS",
    "SO`M": "UZS",
    "SOʻM": "UZS",
    "SO'M.": "UZS",
    "SUM": "UZS",
    "СЎМ": "UZS",
    "СУМ": "UZS",
    "₽": "RUB",
    "РУБ": "RUB",
    "РУБЛЬ": "RUB",
    "RUR": "RUB",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₸": "KZT",
    "ТЕНГЕ": "KZT",
}


def normalize_currency_code(code: str | None, *, default: str = "RUB") -> str:
    """Return a cleaned uppercase currency code (aliases mapped to ISO)."""
    raw = (code or default).strip().upper().replace(" ", "")
    if not raw:
        return default.upper()
    return _ALIASES.get(raw, raw)
