"""Helpers to build currency dropdown options."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import flet as ft

from lib.domain.entities.currency import Currency
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.infrastructure.services.localization import normalize_lang


def _currencies_json_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "data" / "currencies.json"


def load_currency_catalog(*, include_crypto: bool = False) -> list[dict[str, str]]:
    """Load currency rows from bundled JSON (fallback when DB is empty)."""
    path = _currencies_json_path()
    if not path.exists():
        return [
            {
                "code": "RUB",
                "name_ru": "Российский рубль",
                "name_en": "Russian Ruble",
                "name_uz": "Rossiya rubli",
            }
        ]
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for item in data:
        if not include_crypto and item.get("is_crypto"):
            continue
        code = str(item["code"]).upper()
        name_en = str(item.get("name_en") or code)
        name_ru = str(item.get("name_ru") or code)
        name_uz = str(item.get("name_uz") or name_en)
        rows.append(
            {
                "code": code,
                "name_ru": name_ru,
                "name_en": name_en,
                "name_uz": name_uz,
                "symbol": str(item.get("symbol") or code),
            }
        )
    return rows


def _currency_display_name(row: dict[str, str], lang: str) -> str:
    code = normalize_lang(lang)
    if code == "ru":
        return row.get("name_ru") or row.get("name_en") or row["code"]
    if code == "uz":
        return row.get("name_uz") or row.get("name_en") or row["code"]
    return row.get("name_en") or row.get("name_ru") or row["code"]


def currency_dropdown_options(
    currencies: Sequence[Currency] | None = None,
    *,
    lang: str = "ru",
    include_crypto: bool = False,
) -> list[ft.DropdownOption]:
    """Build dropdown options: ``UZS — Узбекский сум``."""
    if currencies:
        rows = [
            {
                "code": c.code.upper(),
                "name_ru": c.name,
                "name_en": c.name,
                "name_uz": c.name,
            }
            for c in currencies
            if include_crypto or not c.is_crypto
        ]
    else:
        rows = load_currency_catalog(include_crypto=include_crypto)

    options: list[ft.DropdownOption] = []
    for row in rows:
        code = normalize_currency_code(row["code"])
        name = _currency_display_name(row, lang)
        options.append(ft.DropdownOption(key=code, text=f"{code} — {name}"))
    return options
