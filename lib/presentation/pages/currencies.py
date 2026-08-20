"""Currencies and exchange rates page with pair converter."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.currency import Currency, ExchangeRate
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.presentation.money_input import make_amount_field, parse_amount
from lib.presentation.styles import card_surface, muted_text, page_header
from lib.presentation.utils import format_money, run_async, safe_convert, snack, tr
from lib.presentation.widgets.currency_ticker_picker import CurrencyTickerPicker
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _format_rate(value: Decimal) -> str:
    """Readable rate: trim trailing zeros, keep meaningful precision."""
    quantized = value.normalize()
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _rates_with_usd_cross(
    base_rates: list,
    usd_rates: list,
    base: str,
) -> list:
    """Fill missing ``base→quote`` rows via the USD book (e.g. UZS→BTC)."""
    base_code = str(base).upper()
    merged = list(base_rates)
    by_quote = {
        str(getattr(rate, "quote", "")).upper(): rate
        for rate in merged
        if getattr(rate, "quote", None)
    }
    usd_per_base: Optional[Decimal] = None
    usd_row = by_quote.get("USD")
    if usd_row is not None and getattr(usd_row, "rate", None):
        usd_per_base = Decimal(str(usd_row.rate))
    if usd_per_base is None:
        inverse = next(
            (
                rate
                for rate in usd_rates
                if str(getattr(rate, "quote", "")).upper() == base_code
                and getattr(rate, "rate", None)
            ),
            None,
        )
        if inverse is not None and inverse.rate:
            usd_per_base = Decimal("1") / Decimal(str(inverse.rate))
    if usd_per_base is None or usd_per_base <= 0:
        return merged

    for usd_row in usd_rates:
        quote = str(getattr(usd_row, "quote", "")).upper()
        if not quote or quote == base_code or quote in by_quote:
            continue
        quote_rate = getattr(usd_row, "rate", None)
        if not quote_rate:
            continue
        derived = usd_per_base * Decimal(str(quote_rate))
        if derived <= 0:
            continue
        merged.append(
            ExchangeRate(
                base=base_code,
                quote=quote,
                rate=derived,
                updated_at=usd_row.updated_at,
            )
        )
        by_quote[quote] = merged[-1]
    return merged


def _matches_query(currency: Currency, query: str) -> bool:
    """Match ticker, name, or symbol (case-insensitive)."""
    if not query:
        return True
    q = query.strip().casefold()
    haystacks = (
        currency.code.casefold(),
        (currency.name or "").casefold(),
        (currency.symbol or "").casefold(),
    )
    return any(q in item for item in haystacks if item)


class CurrenciesPage(ft.Column):
    """Show fiat/crypto rates plus an interactive pair converter."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._currencies: list[Currency] = []
        self._rate_map: dict[str, object] = {}
        self._converting = False

        lang = state.language
        base = state.base_currency
        default_quote = "USD" if base != "USD" else "EUR"

        self._amount = make_amount_field(
            lang,
            label=tr("currencies.amount", lang),
            value="1",
            extra_on_change=lambda _e: run_async(page, self._recalculate),
            expand=True,
            dense=True,
            border_radius=14,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )
        self._amount.on_submit = lambda _e: run_async(page, self._recalculate)
        self._from_picker = CurrencyTickerPicker(
            page,
            lang=lang,
            label=tr("currencies.from", lang),
            value=base,
            include_crypto=True,
            code_only=True,
            on_changed=lambda _code: run_async(page, self._recalculate),
        )
        self._to_picker = CurrencyTickerPicker(
            page,
            lang=lang,
            label=tr("currencies.to", lang),
            value=default_quote,
            include_crypto=True,
            code_only=True,
            on_changed=lambda _code: run_async(page, self._recalculate),
        )
        self._result_value = ft.Text(
            "—",
            size=18,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.PRIMARY,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            text_align=ft.TextAlign.RIGHT,
        )
        self._rate_line = ft.Text(
            "",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=2,
        )
        self._result_hint = ft.Text("", size=11, color=ft.Colors.ERROR, visible=False)

        self._list_search = ft.TextField(
            label=tr("currencies.search", lang),
            hint_text=tr("currencies.search_hint", lang),
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
            on_change=lambda _e: self._render_lists(),
            on_submit=lambda _e: self._apply_search_to_converter(),
        )
        self._base_caption = muted_text("", size=11)
        self._rates_list = ft.ListView(expand=True, spacing=0, padding=ft.Padding.only(bottom=8))
        self._converter = self._build_converter_card(lang)
        self._body = ft.Column(
            expand=True,
            spacing=8,
            controls=[
                self._converter,
                self._list_search,
                self._base_caption,
                self._rates_list,
            ],
        )
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.currencies", lang),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.SYNC,
                            icon_color=ft.Colors.PRIMARY,
                            tooltip=tr("currencies.refresh", lang),
                            on_click=lambda _e: run_async(page, self.refresh_rates),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.only(left=12, right=12, bottom=8),
                    content=self._body,
                ),
            ],
        )
        run_async(page, self.reload)

    def _build_converter_card(self, lang: str) -> ft.Control:
        swap_btn = ft.IconButton(
            icon=ft.Icons.SWAP_HORIZ_ROUNDED,
            icon_color=ft.Colors.PRIMARY,
            tooltip=tr("currencies.swap", lang),
            on_click=lambda _e: run_async(self._page, self._swap_pair),
        )
        return card_surface(
            ft.Column(
                spacing=8,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(expand=True, content=self._amount),
                            ft.Container(
                                expand=True,
                                alignment=ft.Alignment.CENTER_RIGHT,
                                content=self._result_value,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[self._from_picker, swap_btn, self._to_picker],
                    ),
                    self._rate_line,
                    self._result_hint,
                ],
            ),
            padding=12,
        )

    def _selected_pair(self) -> tuple[str, str]:
        src = normalize_currency_code(
            self._from_picker.value or self._state.base_currency
        )
        dst = normalize_currency_code(
            self._to_picker.value or ("USD" if src != "USD" else "EUR")
        )
        return src, dst

    def _parse_amount(self) -> Optional[Decimal]:
        try:
            value = parse_amount(self._amount.value)
        except (InvalidOperation, ValueError):
            return None
        if value < 0:
            return None
        return value

    def _search_query(self) -> str:
        return (self._list_search.value or "").strip()

    def _filtered_currencies(self) -> list[Currency]:
        query = self._search_query()
        return [c for c in self._currencies if _matches_query(c, query)]

    async def _swap_pair(self) -> None:
        src, dst = self._selected_pair()
        self._from_picker.set_value(dst, notify=False)
        self._to_picker.set_value(src, notify=False)
        await self._recalculate()

    async def _recalculate(self) -> None:
        if self._converting:
            return
        self._converting = True
        lang = self._state.language
        try:
            amount = self._parse_amount()
            src, dst = self._selected_pair()
            if amount is None:
                self._result_value.value = "—"
                self._rate_line.value = ""
                self._result_hint.value = tr("invalid_amount", lang)
                self._result_hint.color = ft.Colors.ERROR
                self._update_result()
                return

            converted = await safe_convert(
                self._state.container, amount, src, dst
            )
            one_forward = await safe_convert(
                self._state.container, Decimal("1"), src, dst, quantize=False
            )
            one_reverse = await safe_convert(
                self._state.container, Decimal("1"), dst, src, quantize=False
            )

            if converted is None or one_forward is None or one_reverse is None:
                self._result_value.value = "—"
                self._rate_line.value = ""
                self._result_hint.value = tr("currencies.no_rate", lang)
                self._result_hint.color = ft.Colors.ERROR
            else:
                self._result_value.value = format_money(converted, dst)
                self._rate_line.value = (
                    f"1 {src} = {_format_rate(one_forward)} {dst}"
                    f"  ·  1 {dst} = {_format_rate(one_reverse)} {src}"
                )
                self._result_hint.value = ""
                self._result_hint.color = ft.Colors.ON_SURFACE_VARIANT
            self._update_result()
        finally:
            self._converting = False

    def _update_result(self) -> None:
        self._result_hint.visible = bool(self._result_hint.value)
        self._rate_line.visible = bool(self._rate_line.value)
        for control in (
            self._result_value,
            self._rate_line,
            self._result_hint,
        ):
            try:
                control.update()
            except Exception:  # noqa: BLE001
                pass

    def _tile(self, currency: Currency) -> ft.Control:
        code = currency.code
        rate = self._rate_map.get(code.upper())
        name = currency.name or ""
        trailing = "—"
        if rate is not None:
            trailing = _format_rate(Decimal(str(rate.rate)))  # type: ignore[attr-defined]
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=4, vertical=6),
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            ink=True,
            on_click=lambda _e, c=code: run_async(self._page, self._use_as_quote, c),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(code, width=52, weight=ft.FontWeight.W_700, size=13),
                    ft.Text(
                        name,
                        expand=True,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    ft.Text(trailing, size=12, weight=ft.FontWeight.W_600),
                ],
            ),
        )

    def _section_label(self, text: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.only(top=10, bottom=4),
            content=ft.Text(
                text,
                size=13,
                weight=ft.FontWeight.W_700,
                color=ft.Colors.PRIMARY,
            ),
        )

    def _render_lists(self) -> None:
        lang = self._state.language
        base = self._state.base_currency
        filtered = self._filtered_currencies()
        fiat = [c for c in filtered if not c.is_crypto]
        crypto = [c for c in filtered if c.is_crypto]
        self._base_caption.value = tr("currencies.base_rates", lang, base=base)

        rows: list[ft.Control] = []
        if fiat:
            rows.append(self._section_label(tr("currencies.fiat", lang)))
            rows.extend(self._tile(c) for c in fiat)
        if crypto:
            rows.append(self._section_label(tr("currencies.crypto", lang)))
            rows.extend(self._tile(c) for c in crypto)
        if not filtered and self._search_query():
            rows.append(
                EmptyState(tr("currencies.not_found", lang), icon=ft.Icons.SEARCH_OFF)
            )
        elif not filtered:
            rows.append(muted_text(tr("currencies.not_found", lang), size=12))
        self._rates_list.controls = rows
        try:
            self._base_caption.update()
            self._rates_list.update()
        except Exception:  # noqa: BLE001
            pass

    def _apply_search_to_converter(self) -> None:
        """Enter in search: if exact ticker match, set it as quote currency."""
        query = normalize_currency_code(self._search_query())
        if not query:
            return
        match = next(
            (c for c in self._currencies if c.code.upper() == query),
            None,
        )
        if match is None:
            filtered = self._filtered_currencies()
            if len(filtered) == 1:
                match = filtered[0]
        if match is None:
            return
        run_async(self._page, self._use_as_quote, match.code)

    async def reload(self) -> None:
        """Load currencies and known rates vs base currency."""
        lang = self._state.language
        self._rates_list.controls = [loading_indicator()]
        try:
            self._rates_list.update()
        except Exception:  # noqa: BLE001
            pass

        base = self._state.base_currency
        try:
            currencies = await self._state.container.list_currencies.execute(
                include_crypto=True
            )
            self._currencies = list(currencies)
            repo = self._state.container.currency_repository
            rates = []
            if repo is not None and hasattr(repo, "list_rates"):
                rates = await repo.list_rates(base=base)
                usd_book = (
                    await repo.list_rates(base="USD")
                    if str(base).upper() != "USD"
                    else []
                )
                rates = _rates_with_usd_cross(rates, usd_book, base)
            elif repo is not None and hasattr(repo, "list_all_rates"):
                rates = await repo.list_all_rates()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._rates_list.controls = [EmptyState(tr("error.generic", lang))]
            try:
                self._rates_list.update()
            except Exception:  # noqa: BLE001
                pass
            return

        self._from_picker.set_currencies(self._currencies)
        self._to_picker.set_currencies(self._currencies)
        codes = {c.code.upper() for c in self._currencies}
        src, dst = self._selected_pair()
        if src not in codes and self._currencies:
            self._from_picker.set_value(self._currencies[0].code, notify=False)
            src = self._currencies[0].code.upper()
        if dst not in codes or dst == src:
            fallback = next((c for c in codes if c != src), src)
            self._to_picker.set_value(fallback, notify=False)

        rate_map: dict[str, object] = {}
        for rate in rates:
            quote = getattr(rate, "quote", None)
            if quote:
                rate_map[str(quote).upper()] = rate
        self._rate_map = rate_map

        self._render_lists()
        await self._recalculate()

    async def _use_as_quote(self, code: str) -> None:
        """Tap a rate row to set it as the converter target."""
        code = normalize_currency_code(code)
        src, _dst = self._selected_pair()
        if code == src:
            self._from_picker.set_value(self._to_picker.value or src, notify=False)
        self._to_picker.set_value(code, notify=False)
        await self._recalculate()

    async def refresh_rates(self) -> None:
        """Manually refresh exchange rates via use case."""
        lang = self._state.language
        try:
            await self._state.container.update_exchange_rates.execute(
                base=self._state.base_currency
            )
            snack(self._page, tr("action.saved", lang))
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
        await self.reload()
