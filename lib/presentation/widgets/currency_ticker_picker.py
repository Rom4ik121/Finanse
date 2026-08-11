"""Searchable currency ticker picker (dialog with live filter)."""

from __future__ import annotations

from typing import Callable, Optional, Sequence

import flet as ft

from lib.domain.entities.currency import Currency
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.presentation.currency_options import (
    _currency_display_name,
    load_currency_catalog,
)
from lib.presentation.utils import tr


def _rows_from_currencies(
    currencies: Sequence[Currency] | None,
    *,
    lang: str,
) -> list[dict[str, str]]:
    if currencies:
        return [
            {
                "code": c.code.upper(),
                "name": c.name,
                "symbol": c.symbol or c.code,
            }
            for c in currencies
        ]
    catalog = load_currency_catalog(include_crypto=True)
    return [
        {
            "code": row["code"],
            "name": _currency_display_name(row, lang),
            "symbol": row["code"],
        }
        for row in catalog
    ]


def _label_for(code: str, rows: Sequence[dict[str, str]]) -> str:
    code = normalize_currency_code(code)
    for row in rows:
        if row["code"] == code:
            return f"{code} — {row['name']}"
    return code


class CurrencyTickerPicker(ft.Container):
    """Field that opens a searchable ticker list when tapped."""

    def __init__(
        self,
        page: ft.Page,
        *,
        lang: str,
        label: str,
        value: str,
        currencies: Sequence[Currency] | None = None,
        on_changed: Optional[Callable[[str], None]] = None,
        expand: bool = True,
    ) -> None:
        self._page = page
        self._lang = lang
        self._label = label
        self._on_changed = on_changed
        self._rows = _rows_from_currencies(currencies, lang=lang)
        self._value = normalize_currency_code(value)

        self._display = ft.Text(
            _label_for(self._value, self._rows),
            size=14,
            weight=ft.FontWeight.W_600,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            expand=True,
        )
        self._caption = ft.Text(
            label,
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        super().__init__(
            expand=expand,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            ink=True,
            on_click=lambda _e: self.open(),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[self._caption, self._display],
                    ),
                    ft.Icon(
                        ft.Icons.SEARCH,
                        size=18,
                        color=ft.Colors.PRIMARY,
                    ),
                ],
            ),
        )

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, code: str) -> None:
        self.set_value(code, notify=False)

    def set_currencies(self, currencies: Sequence[Currency]) -> None:
        """Refresh catalog used by the picker dialog."""
        self._rows = _rows_from_currencies(currencies, lang=self._lang)
        self._display.value = _label_for(self._value, self._rows)
        try:
            self._display.update()
        except Exception:  # noqa: BLE001
            pass

    def set_value(self, code: str, *, notify: bool = True) -> None:
        self._value = normalize_currency_code(code)
        self._display.value = _label_for(self._value, self._rows)
        try:
            self._display.update()
        except Exception:  # noqa: BLE001
            pass
        if notify and self._on_changed is not None:
            self._on_changed(self._value)

    def open(self) -> None:
        """Open searchable ticker dialog."""
        lang = self._lang
        list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        search = ft.TextField(
            label=tr("currencies.search", lang),
            hint_text=tr("currencies.search_hint", lang),
            prefix_icon=ft.Icons.SEARCH,
            autofocus=True,
            dense=True,
            border_radius=14,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )

        def _matches(row: dict[str, str], query: str) -> bool:
            if not query:
                return True
            q = query.strip().casefold()
            return q in row["code"].casefold() or q in row["name"].casefold()

        def _fill(query: str = "") -> None:
            rows = [r for r in self._rows if _matches(r, query)]
            # Prefer ticker prefix matches first.
            q = query.strip().casefold()
            if q:
                rows.sort(
                    key=lambda r: (
                        0 if r["code"].casefold().startswith(q) else 1,
                        r["code"],
                    )
                )
            else:
                rows.sort(key=lambda r: r["code"])

            if not rows:
                list_col.controls = [
                    ft.Container(
                        padding=16,
                        content=ft.Text(
                            tr("currencies.not_found", lang),
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    )
                ]
            else:
                list_col.controls = [
                    ft.ListTile(
                        leading=ft.CircleAvatar(
                            content=ft.Text(row["code"][:3], size=11)
                        ),
                        title=ft.Text(row["code"], weight=ft.FontWeight.W_700),
                        subtitle=ft.Text(row["name"], size=12),
                        selected=row["code"] == self._value,
                        on_click=lambda _e, code=row["code"]: _pick(code),
                    )
                    for row in rows[:120]
                ]
            try:
                list_col.update()
            except Exception:  # noqa: BLE001
                pass

        def _pick(code: str) -> None:
            self._page.pop_dialog()
            self.set_value(code, notify=True)

        def _on_search(_e: ft.ControlEvent) -> None:
            _fill(search.value or "")

        def _on_submit(_e: ft.ControlEvent) -> None:
            query = normalize_currency_code(search.value or "")
            if not query:
                return
            exact = next((r for r in self._rows if r["code"] == query), None)
            if exact is not None:
                _pick(exact["code"])
                return
            filtered = [r for r in self._rows if _matches(r, search.value or "")]
            if len(filtered) == 1:
                _pick(filtered[0]["code"])

        search.on_change = _on_search
        search.on_submit = _on_submit
        _fill("")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self._label),
            content=ft.Container(
                width=420,
                height=420,
                content=ft.Column(
                    spacing=10,
                    expand=True,
                    controls=[search, list_col],
                ),
            ),
            actions=[
                ft.TextButton(
                    tr("action.cancel", lang),
                    on_click=lambda _e: self._page.pop_dialog(),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dialog)
