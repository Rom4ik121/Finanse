"""Currencies and exchange rates page with pair converter."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.currency import Currency
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.presentation.styles import card_surface, muted_text, page_header, section_title
from lib.presentation.utils import format_date, format_money, run_async, safe_convert, snack, tr
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

        self._amount = ft.TextField(
            label=tr("currencies.amount", lang),
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            dense=True,
            border_radius=14,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
            on_change=lambda _e: run_async(page, self._recalculate),
            on_submit=lambda _e: run_async(page, self._recalculate),
        )
        self._from_picker = CurrencyTickerPicker(
            page,
            lang=lang,
            label=tr("currencies.from", lang),
            value=base,
            on_changed=lambda _code: run_async(page, self._recalculate),
        )
        self._to_picker = CurrencyTickerPicker(
            page,
            lang=lang,
            label=tr("currencies.to", lang),
            value=default_quote,
            on_changed=lambda _code: run_async(page, self._recalculate),
        )
        self._result_value = ft.Text(
            "—",
            size=26,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.PRIMARY,
        )
        self._rate_forward = muted_text("—", size=13)
        self._rate_reverse = muted_text("—", size=13)
        self._result_hint = muted_text(tr("currencies.compare_hint", lang), size=12)

        self._list_search = ft.TextField(
            label=tr("currencies.search", lang),
            hint_text=tr("currencies.search_hint", lang),
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            border_radius=14,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
            on_change=lambda _e: self._render_lists(),
            on_submit=lambda _e: self._apply_search_to_converter(),
        )
        self._fiat_list = ft.Column(spacing=4)
        self._crypto_list = ft.Column(spacing=4)
        self._fiat_section = ft.Column(spacing=8, tight=True)
        self._crypto_section = ft.Column(spacing=8, tight=True)
        self._lists_host = ft.Column(spacing=14)
        self._body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                self._build_converter_card(lang),
                self._lists_host,
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
                        ft.FilledButton(
                            tr("currencies.refresh", lang),
                            icon=ft.Icons.SYNC,
                            on_click=lambda _e: run_async(page, self.refresh_rates),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=16),
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
                spacing=14,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=40,
                                height=40,
                                border_radius=12,
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.COMPARE_ARROWS_ROUNDED,
                                    color=ft.Colors.ON_PRIMARY_CONTAINER,
                                    size=22,
                                ),
                            ),
                            ft.Column(
                                spacing=2,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        tr("currencies.compare", lang),
                                        size=16,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                    muted_text(
                                        tr("currencies.compare_hint", lang),
                                        size=12,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    self._amount,
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[self._from_picker, swap_btn, self._to_picker],
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=14, vertical=14),
                        border_radius=14,
                        bgcolor=ft.Colors.SURFACE,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        content=ft.Column(
                            spacing=8,
                            tight=True,
                            controls=[
                                muted_text(tr("currencies.result", lang), size=11),
                                self._result_value,
                                self._rate_forward,
                                self._rate_reverse,
                                self._result_hint,
                            ],
                        ),
                    ),
                ],
            )
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
        raw = (self._amount.value or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            return None
        try:
            value = Decimal(raw)
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
                self._rate_forward.value = "—"
                self._rate_reverse.value = "—"
                self._result_hint.value = tr("invalid_amount", lang)
                self._result_hint.color = ft.Colors.ERROR
                self._update_result()
                return

            converted = await safe_convert(
                self._state.container, amount, src, dst
            )
            one_forward = await safe_convert(
                self._state.container, Decimal("1"), src, dst
            )
            one_reverse = await safe_convert(
                self._state.container, Decimal("1"), dst, src
            )

            if converted is None or one_forward is None or one_reverse is None:
                self._result_value.value = "—"
                self._rate_forward.value = "—"
                self._rate_reverse.value = "—"
                self._result_hint.value = tr("currencies.no_rate", lang)
                self._result_hint.color = ft.Colors.ERROR
            else:
                self._result_value.value = format_money(converted, dst)
                self._rate_forward.value = tr(
                    "currencies.unit_rate",
                    lang,
                    src=src,
                    dst=dst,
                    rate=_format_rate(one_forward),
                )
                self._rate_reverse.value = tr(
                    "currencies.unit_rate",
                    lang,
                    src=dst,
                    dst=src,
                    rate=_format_rate(one_reverse),
                )
                self._result_hint.value = f"{format_money(amount, src)} → {dst}"
                self._result_hint.color = ft.Colors.ON_SURFACE_VARIANT
            self._update_result()
        finally:
            self._converting = False

    def _update_result(self) -> None:
        for control in (
            self._result_value,
            self._rate_forward,
            self._rate_reverse,
            self._result_hint,
        ):
            try:
                control.update()
            except Exception:  # noqa: BLE001
                pass

    def _tile(self, currency: Currency) -> ft.Control:
        code = currency.code
        rate = self._rate_map.get(code.upper())
        subtitle = f"{currency.symbol} · {currency.name}"
        trailing = "—"
        if rate is not None:
            trailing = _format_rate(Decimal(str(rate.rate)))  # type: ignore[attr-defined]
            subtitle += f" · {format_date(rate.updated_at, with_time=True)}"  # type: ignore[attr-defined]
        return ft.ListTile(
            leading=ft.CircleAvatar(content=ft.Text(code[:3], size=11)),
            title=ft.Text(code, weight=ft.FontWeight.W_600),
            subtitle=ft.Text(subtitle, size=12),
            trailing=ft.Text(trailing, weight=ft.FontWeight.W_600),
            on_click=lambda _e, c=code: run_async(
                self._page, self._use_as_quote, c
            ),
        )

    def _render_lists(self) -> None:
        lang = self._state.language
        base = self._state.base_currency
        filtered = self._filtered_currencies()
        fiat = [c for c in filtered if not c.is_crypto]
        crypto = [c for c in filtered if c.is_crypto]

        self._fiat_list.controls = [self._tile(c) for c in fiat]
        self._crypto_list.controls = [self._tile(c) for c in crypto]

        self._fiat_section.controls = [
            section_title(tr("currencies.fiat", lang)),
            self._fiat_list
            if fiat
            else muted_text(tr("currencies.not_found", lang), size=12),
        ]
        self._crypto_section.controls = [
            section_title(tr("currencies.crypto", lang)),
            self._crypto_list
            if crypto
            else muted_text(tr("currencies.not_found", lang), size=12),
        ]

        self._lists_host.controls = [
            section_title(tr("currencies.base_rates", lang, base=base)),
            self._list_search,
            muted_text(f"1 {base} = …", size=12),
            self._fiat_section,
            self._crypto_section,
        ]
        if not filtered and self._search_query():
            self._lists_host.controls.append(
                EmptyState(tr("currencies.not_found", lang), icon=ft.Icons.SEARCH_OFF)
            )
        try:
            self._lists_host.update()
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
        self._lists_host.controls = [loading_indicator()]
        try:
            self._lists_host.update()
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
            elif repo is not None and hasattr(repo, "list_all_rates"):
                rates = await repo.list_all_rates()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._lists_host.controls = [EmptyState(tr("error.generic", lang))]
            try:
                self._lists_host.update()
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
