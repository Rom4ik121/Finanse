"""Account icon keys: thematic Material icons + currency/crypto glyphs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import flet as ft

from lib.core.config import ACCOUNT_ICON_GROUPS, ACCOUNT_ICONS
from lib.presentation.icon_registry import resolve_icon

CURRENCY_ICON_PREFIX = "ccy_"


def currency_icon_key(code: str) -> str:
    """Build a stored icon key for a currency code."""
    return f"{CURRENCY_ICON_PREFIX}{code.strip().upper()}"


def parse_currency_icon_key(key: str | None) -> str | None:
    """Return currency code when ``key`` is a currency glyph key."""
    if not key or not key.startswith(CURRENCY_ICON_PREFIX):
        return None
    code = key[len(CURRENCY_ICON_PREFIX) :].strip().upper()
    return code or None


def _currencies_json_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "data" / "currencies.json"


@lru_cache(maxsize=1)
def _currency_catalog() -> tuple[dict[str, str], ...]:
    path = _currencies_json_path()
    if not path.exists():
        return (
            {"code": "RUB", "symbol": "₽", "is_crypto": "0"},
            {"code": "USD", "symbol": "$", "is_crypto": "0"},
            {"code": "EUR", "symbol": "€", "is_crypto": "0"},
            {"code": "BTC", "symbol": "₿", "is_crypto": "1"},
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for item in data:
        rows.append(
            {
                "code": str(item["code"]).upper(),
                "symbol": str(item.get("symbol") or item["code"]),
                "is_crypto": "1" if item.get("is_crypto") else "0",
            }
        )
    return tuple(rows)


# Distinct 1–2 character marks for well-known coins (catalog tiles).
_CRYPTO_GLYPHS: dict[str, str] = {
    "BTC": "₿",
    "ETH": "Ξ",
    "USDT": "₮",
    "USDC": "$",
    "BNB": "B",
    "XRP": "✕",
    "SOL": "S",
    "TRX": "T",
    "DOGE": "Ð",
    "LTC": "Ł",
    "XMR": "ɱ",
    "ZEC": "ⓩ",
    "ADA": "A",
    "DOT": "●",
    "TON": "◎",
    "SHIB": "š",
    "PEPE": "P",
    "DAI": "◈",
    "LINK": "⬡",
    "AVAX": "A",
    "MATIC": "M",
    "POL": "M",
    "ATOM": "⚛",
    "XLM": "*",
    "BCH": "฿",
    "ETC": "ξ",
    "FIL": "⨎",
    "UNI": "U",
    "AAVE": "A",
    "NEAR": "N",
    "APT": "A",
    "ARB": "A",
    "SUI": "S",
    "HBAR": "ℏ",
    "CRO": "C",
    "OKB": "O",
    "KCS": "K",
    "ALGO": "A",
    "QNT": "Q",
    "RENDER": "R",
    "JUP": "J",
    "PI": "π",
    "KAS": "K",
    "MNT": "M",
    "TAO": "τ",
    "PAXG": "Au",
    "XAUT": "Au",
}


def currency_glyph_label(code: str, symbol: str | None = None) -> str:
    """Short label for a currency tile (symbol if compact, else ticker)."""
    code = code.upper()
    glyph = _CRYPTO_GLYPHS.get(code)
    if glyph:
        return glyph
    if symbol is None:
        for row in _currency_catalog():
            if row["code"] == code:
                symbol = row["symbol"]
                break
    text = (symbol or code).strip()
    if text and len(text) <= 2:
        return text
    if text and len(text) <= 3 and not text.isascii():
        return text
    return code if len(code) <= 4 else code[:4]


def account_icon_groups() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Thematic groups plus fiat / crypto currency glyph groups."""
    fiat_keys: list[str] = []
    crypto_keys: list[str] = []
    for row in _currency_catalog():
        key = currency_icon_key(row["code"])
        if row["is_crypto"] == "1":
            crypto_keys.append(key)
        else:
            fiat_keys.append(key)
    extra: list[tuple[str, tuple[str, ...]]] = []
    if fiat_keys:
        extra.append(("icon_group.fiat", tuple(fiat_keys)))
    if crypto_keys:
        extra.append(("icon_group.crypto", tuple(crypto_keys)))
    return ACCOUNT_ICON_GROUPS + tuple(extra)


def all_account_icon_keys() -> tuple[str, ...]:
    """Flat unique list of valid account icon keys (themes + currencies)."""
    keys: list[str] = list(ACCOUNT_ICONS)
    for _label, group in account_icon_groups():
        keys.extend(group)
    return tuple(dict.fromkeys(keys))


def crypto_icon_keys() -> tuple[str, ...]:
    """Stored keys for every crypto ticker in the bundled catalog."""
    return tuple(
        currency_icon_key(row["code"])
        for row in _currency_catalog()
        if row["is_crypto"] == "1"
    )


def is_valid_account_icon(key: str | None) -> bool:
    if not key:
        return False
    if key in ACCOUNT_ICONS:
        return True
    return parse_currency_icon_key(key) is not None


def account_icon_control(
    key: str | None,
    *,
    size: float = 20,
    color: str | None = None,
) -> ft.Control:
    """Build an Icon or currency-symbol Text for a stored account icon key."""
    code = parse_currency_icon_key(key)
    if code is not None:
        label = currency_glyph_label(code)
        # Compact codes (USDT, MATIC) need a smaller type size.
        if len(label) >= 4:
            font_size = max(8, int(size * 0.38))
        elif len(label) == 3:
            font_size = max(9, int(size * 0.45))
        else:
            font_size = max(11, int(size * 0.58))
        return ft.Text(
            label,
            size=font_size,
            weight=ft.FontWeight.W_700,
            color=color,
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
        )
    return ft.Icon(
        resolve_icon(key, default="wallet"),
        size=size,
        color=color,
    )
