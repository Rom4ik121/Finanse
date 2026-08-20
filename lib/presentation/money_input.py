"""Locale-aware amount typing: group thousands with ``.`` or ``,``."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Optional

import flet as ft

from lib.infrastructure.services.localization import normalize_lang


def amount_separators(lang: str) -> tuple[str, str]:
    """Return ``(thousands, decimal)`` for the UI language.

    English uses ``1,234.50``; Russian and Uzbek use ``1.234,50``.
    """
    if normalize_lang(lang) == "en":
        return ",", "."
    return ".", ","


def parse_amount(text: str | None) -> Decimal:
    """Parse a grouped amount into ``Decimal``.

    Raises ``InvalidOperation`` when the field is empty or not a number.
    """
    int_digits, frac, trailing = _split_int_frac(text)
    if trailing and not frac:
        frac = ""
    if not int_digits and not frac:
        raise InvalidOperation("empty amount")
    raw = f"{int_digits or '0'}.{frac}" if frac is not None else (int_digits or "0")
    return Decimal(raw)


def format_amount_input(text: str, lang: str) -> str:
    """Re-group digits in a live amount field without dropping a trailing decimal."""
    thousands, decimal = amount_separators(lang)
    stripped = (text or "").strip()
    if not stripped or stripped in {"-", "−"}:
        return "-" if stripped.startswith(("-", "−")) else ""
    negative = stripped.startswith(("-", "−"))
    int_digits, frac, trailing = _split_int_frac(text)
    if int_digits is None:
        return text
    grouped = _group_int(int_digits, thousands)
    if trailing or frac is not None:
        out = f"{grouped}{decimal}{frac or ''}"
    else:
        out = grouped
    return f"-{out}" if negative else out


def format_amount_value(value: object, lang: str) -> str:
    """Format a stored amount for an editable field."""
    if value is None or value == "":
        return ""
    try:
        quantized = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, ArithmeticError):
        return format_amount_input(str(value), lang)
    if quantized == quantized.to_integral_value():
        text = str(int(abs(quantized)))
    else:
        text = f"{abs(quantized):.2f}"
    formatted = format_amount_input(text, lang)
    return f"-{formatted}" if quantized < 0 else formatted


def attach_grouped_digits(
    field: ft.TextField,
    lang: str,
    *,
    extra_on_change: Optional[Callable[[ft.ControlEvent], Any]] = None,
) -> ft.TextField:
    """Keep ``field`` grouped as the user types; optionally chain another handler."""

    def _on_change(e: ft.ControlEvent) -> None:
        current = field.value or ""
        formatted = format_amount_input(current, lang)
        if formatted != current:
            field.value = formatted
            try:
                field.update()
            except Exception:  # noqa: BLE001
                pass
        if extra_on_change is not None:
            extra_on_change(e)

    field.on_change = _on_change
    field.on_blur = _on_change
    return field


def make_amount_field(
    lang: str,
    *,
    label: str,
    value: object = "",
    extra_on_change: Optional[Callable[[ft.ControlEvent], Any]] = None,
    **kwargs: Any,
) -> ft.TextField:
    """Build a numeric TextField that groups thousands while typing."""
    field = ft.TextField(
        label=label,
        value=format_amount_value(value, lang) if value not in (None, "") else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        **kwargs,
    )
    return attach_grouped_digits(field, lang, extra_on_change=extra_on_change)


def _group_int(digits: str, sep: str) -> str:
    if not digits:
        return "0"
    trimmed = digits.lstrip("0")
    if not trimmed:
        return "0"
    parts: list[str] = []
    while trimmed:
        parts.append(trimmed[-3:])
        trimmed = trimmed[:-3]
    return sep.join(reversed(parts))


def _split_int_frac(text: str | None) -> tuple[Optional[str], Optional[str], bool]:
    """Split typed text into integer digits, optional fraction, trailing-decimal flag.

    A separator is decimal only when it is the last one and 1–2 digits follow
    (or nothing, if the user just typed it). Longer tails are thousands:
    ``1,000000`` → 1_000_000, not 1.000000.
    """
    if text is None:
        return None, None, False
    s = str(text).strip().replace("−", "-")
    if s.startswith("-"):
        s = s[1:]
    s = s.replace(" ", "").replace("\u00a0", "").replace("'", "")
    raw = "".join(c for c in s if c.isdigit() or c in ".,")
    if not raw:
        return "", None, False

    trailing = raw.endswith(".") or raw.endswith(",")
    digits_only = "".join(c for c in raw if c.isdigit())

    if "," in raw and "." in raw:
        dec_pos = max(raw.rfind(","), raw.rfind("."))
        int_digits = "".join(c for c in raw[:dec_pos] if c.isdigit())
        frac = "".join(c for c in raw[dec_pos + 1 :] if c.isdigit())
        if trailing and not frac:
            return int_digits, "", True
        if len(frac) <= 2:
            return int_digits, frac, False
        return digits_only, None, False

    sep = "," if "," in raw else ("." if "." in raw else None)
    if sep is None:
        return digits_only, None, False

    parts = raw.split(sep)
    if trailing:
        int_digits = "".join(p for p in parts if p)
        return int_digits, "", True
    last = parts[-1]
    head = "".join(parts[:-1])
    if 1 <= len(last) <= 2:
        return head, last, False
    return "".join(parts), None, False
