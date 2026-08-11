"""Compact date / date-time field with an inline calendar panel.

The calendar expands inside the parent form. Flet cannot reliably stack a
second ``AlertDialog`` / ``DatePicker`` on top of an open dialog (grey
barrier with no UI), so we never call ``show_dialog`` here.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Callable, Optional

import flet as ft

from lib.infrastructure.services.localization import normalize_lang
from lib.presentation.utils import format_date, tr


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _display_text(
    value: Optional[datetime],
    *,
    with_time: bool,
    empty_label: str,
) -> str:
    if value is None:
        return empty_label
    return format_date(value, with_time=with_time)


def picker_locale(lang: str | None) -> str:
    """Map app language code to a locale tag (kept for tests / callers)."""
    code = normalize_lang(lang)
    return {
        "ru": "ru_RU",
        "en": "en_US",
        "uz": "uz_UZ",
    }.get(code, "ru_RU")


_MONTHS: dict[str, tuple[str, ...]] = {
    "ru": (
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ),
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "uz": (
        "Yanvar",
        "Fevral",
        "Mart",
        "Aprel",
        "May",
        "Iyun",
        "Iyul",
        "Avgust",
        "Sentabr",
        "Oktabr",
        "Noyabr",
        "Dekabr",
    ),
}

_WEEKDAYS: dict[str, tuple[str, ...]] = {
    "ru": ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"),
    "en": ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"),
    "uz": ("Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"),
}


class DateTimeField(ft.Column):
    """Compact date control: set/change via an inline calendar panel."""

    def __init__(
        self,
        page: ft.Page,
        *,
        lang: str,
        label: str | None = None,
        value: Optional[datetime] = None,
        with_time: bool = False,
        allow_clear: bool = False,
        first_date: Optional[date] = None,
        last_date: Optional[date] = None,
        on_changed: Optional[Callable[[Optional[datetime]], None]] = None,
        expand: bool = False,
    ) -> None:
        self._page = page
        self._lang = normalize_lang(lang)
        self._label = label or tr("field.date", lang)
        self._with_time = with_time
        self._allow_clear = allow_clear
        self._on_changed = on_changed
        self._first_date = first_date or date(2000, 1, 1)
        self._last_date = last_date or date(2100, 12, 31)
        self._value: Optional[datetime] = _as_utc(value) if value else None
        self._picker_open = False
        self._pick_state: dict[str, int] | None = None

        self._title = ft.Text(
            self._label,
            size=12,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._value_text = ft.Text(
            "",
            size=14,
            weight=ft.FontWeight.W_600,
            expand=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
        )
        self._set_btn = ft.OutlinedButton(
            tr("date.set_with_time", lang) if with_time else tr("date.set", lang),
            icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
            on_click=lambda _e: self.open_picker(),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
            ),
        )
        self._change_btn = ft.TextButton(
            tr("date.change", lang),
            icon=ft.Icons.EDIT_CALENDAR_OUTLINED,
            on_click=lambda _e: self.open_picker(),
        )
        self._clear_btn = ft.IconButton(
            icon=ft.Icons.CLOSE_ROUNDED,
            icon_size=18,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            tooltip=tr("date.clear", lang),
            visible=allow_clear,
            on_click=lambda _e: self.clear(),
        )
        self._selected_row = ft.Container(
            visible=False,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_AVAILABLE_ROUNDED,
                        size=18,
                        color=ft.Colors.PRIMARY,
                    ),
                    self._value_text,
                    self._change_btn,
                    self._clear_btn,
                ],
            ),
        )

        self._month_title = ft.Text("", size=15, weight=ft.FontWeight.W_700)
        self._grid = ft.Column(spacing=2, tight=True)
        self._hour_dd = ft.Dropdown(
            label=tr("date.hour", lang),
            dense=True,
            expand=True,
            visible=with_time,
            options=[
                ft.DropdownOption(key=f"{h:02d}", text=f"{h:02d}") for h in range(24)
            ],
        )
        self._minute_dd = ft.Dropdown(
            label=tr("date.minute", lang),
            dense=True,
            expand=True,
            visible=with_time,
            options=[
                ft.DropdownOption(key=f"{m:02d}", text=f"{m:02d}")
                for m in range(0, 60, 5)
            ],
        )
        time_row = ft.Row(
            spacing=8,
            visible=with_time,
            controls=[self._hour_dd, self._minute_dd],
        )
        self._panel = ft.Container(
            visible=False,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=ft.padding.all(10),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(
                        tr("date.pick", lang),
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                icon_size=20,
                                icon_color=ft.Colors.PRIMARY,
                                on_click=lambda _e: self._shift_month(-1),
                            ),
                            self._month_title,
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                icon_size=20,
                                icon_color=ft.Colors.PRIMARY,
                                on_click=lambda _e: self._shift_month(1),
                            ),
                        ],
                    ),
                    self._grid,
                    time_row,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        spacing=4,
                        controls=[
                            ft.TextButton(
                                tr("action.cancel", lang),
                                on_click=lambda _e: self._close_picker(),
                            ),
                            ft.FilledButton(
                                tr("action.apply", lang),
                                on_click=lambda _e: self._apply_picker(),
                            ),
                        ],
                    ),
                ],
            ),
        )

        super().__init__(
            spacing=6,
            tight=True,
            expand=expand,
            controls=[
                self._title,
                self._set_btn,
                self._selected_row,
                self._panel,
            ],
        )
        self._sync_ui()

    @property
    def value(self) -> Optional[datetime]:
        """Selected UTC datetime (date-only at 00:00 when without time)."""
        return self._value

    @value.setter
    def value(self, dt: Optional[datetime]) -> None:
        self.set_value(dt, notify=False)

    @property
    def date_text(self) -> str:
        """``YYYY-MM-DD`` for filters, or empty when unset."""
        if self._value is None:
            return ""
        return self._value.date().isoformat()

    def set_value(
        self,
        dt: Optional[datetime],
        *,
        notify: bool = True,
    ) -> None:
        self._value = _as_utc(dt) if dt is not None else None
        self._sync_ui()
        if notify and self._on_changed is not None:
            self._on_changed(self._value)

    def clear(self) -> None:
        if not self._allow_clear:
            return
        self._close_picker()
        self.set_value(None, notify=True)

    def _sync_ui(self) -> None:
        has_value = self._value is not None
        self._set_btn.visible = not has_value and not self._picker_open
        self._selected_row.visible = has_value and not self._picker_open
        self._clear_btn.visible = has_value and self._allow_clear
        self._panel.visible = self._picker_open
        if has_value:
            self._value_text.value = format_date(
                self._value, with_time=self._with_time
            )
        else:
            self._value_text.value = ""
        for control in (
            self._set_btn,
            self._selected_row,
            self._clear_btn,
            self._value_text,
            self._panel,
        ):
            try:
                control.update()
            except Exception:  # noqa: BLE001
                pass

    def open_picker(self) -> None:
        """Expand the inline calendar (safe inside an open AlertDialog)."""
        initial = (self._value or datetime.now(timezone.utc)).date()
        if initial < self._first_date:
            initial = self._first_date
        if initial > self._last_date:
            initial = self._last_date
        now = self._value or datetime.now(timezone.utc)
        self._pick_state = {
            "year": initial.year,
            "month": initial.month,
            "day": initial.day,
            "hour": now.hour,
            "minute": now.minute,
        }
        self._hour_dd.value = f"{now.hour:02d}"
        minute = now.minute - (now.minute % 5) if now.minute % 5 else now.minute
        if self._with_time and now.minute % 5 != 0:
            key = f"{now.minute:02d}"
            if not any(opt.key == key for opt in self._minute_dd.options or []):
                self._minute_dd.options = list(self._minute_dd.options or []) + [
                    ft.DropdownOption(key=key, text=key)
                ]
            self._minute_dd.value = key
        else:
            self._minute_dd.value = f"{minute:02d}"
        self._picker_open = True
        self._render_grid()
        self._sync_ui()

    def _close_picker(self) -> None:
        self._picker_open = False
        self._pick_state = None
        self._sync_ui()

    def _apply_picker(self) -> None:
        state = self._pick_state
        if state is None:
            return
        hour = int(self._hour_dd.value or state["hour"]) if self._with_time else 0
        minute = (
            int(self._minute_dd.value or state["minute"]) if self._with_time else 0
        )
        chosen = datetime(
            state["year"],
            state["month"],
            state["day"],
            hour,
            minute,
            tzinfo=timezone.utc,
        )
        self._picker_open = False
        self._pick_state = None
        self.set_value(chosen, notify=True)

    def _clamp_day(self) -> None:
        state = self._pick_state
        if state is None:
            return
        last = calendar.monthrange(state["year"], state["month"])[1]
        if state["day"] > last:
            state["day"] = last

    def _shift_month(self, delta: int) -> None:
        state = self._pick_state
        if state is None:
            return
        month = state["month"] + delta
        year = state["year"]
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        state["month"] = month
        state["year"] = year
        self._clamp_day()
        self._render_grid()

    def _render_grid(self) -> None:
        state = self._pick_state
        if state is None:
            return
        lang = self._lang
        months = _MONTHS.get(lang, _MONTHS["en"])
        weekdays = _WEEKDAYS.get(lang, _WEEKDAYS["en"])
        self._month_title.value = f"{months[state['month'] - 1]} {state['year']}"
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(
            state["year"], state["month"]
        )
        header = ft.Row(
            spacing=2,
            controls=[
                ft.Container(
                    width=34,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        name,
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
                for name in weekdays
            ],
        )
        rows: list[ft.Control] = [header]
        today = date.today()
        for week in weeks:
            cells: list[ft.Control] = []
            for day_num in week:
                if day_num == 0:
                    cells.append(ft.Container(width=34, height=34))
                    continue
                current = date(state["year"], state["month"], day_num)
                disabled = current < self._first_date or current > self._last_date
                selected = day_num == state["day"]
                is_today = current == today

                def _pick(_e: ft.ControlEvent, d: int = day_num) -> None:
                    if self._pick_state is None:
                        return
                    self._pick_state["day"] = d
                    self._render_grid()

                bg = None
                fg = ft.Colors.ON_SURFACE
                if selected:
                    bg = ft.Colors.PRIMARY
                    fg = ft.Colors.ON_PRIMARY
                elif is_today:
                    bg = ft.Colors.PRIMARY_CONTAINER
                    fg = ft.Colors.ON_PRIMARY_CONTAINER

                cells.append(
                    ft.Container(
                        width=34,
                        height=34,
                        border_radius=17,
                        bgcolor=bg,
                        alignment=ft.Alignment.CENTER,
                        ink=not disabled,
                        opacity=0.35 if disabled else 1.0,
                        on_click=None if disabled else _pick,
                        content=ft.Text(
                            str(day_num),
                            size=12,
                            weight=ft.FontWeight.W_600
                            if selected or is_today
                            else None,
                            color=fg,
                        ),
                    )
                )
            rows.append(ft.Row(spacing=2, controls=cells))
        self._grid.controls = rows
        try:
            self._month_title.update()
            self._grid.update()
            self._hour_dd.update()
            self._minute_dd.update()
        except Exception:  # noqa: BLE001
            pass
