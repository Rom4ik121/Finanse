"""Debts CRUD page with filters, projection, and payment history."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.use_cases.debts import compute_debt_interest, debt_credit_amount
from lib.presentation.notification_badges import (
    DEBT_ALERT_KINDS,
    mark_related_read,
    pending_related_ids,
)
from lib.presentation.styles import (
    card_surface,
    muted_text,
    page_header,
    summary_strip,
)
from lib.presentation.utils import (
    format_date,
    format_money,
    load_rate_book,
    run_async,
    snack,
    tr,
)
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.currency_ticker_picker import CurrencyTickerPicker
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.debt_card import DebtCard
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_PAYMENT_PAGE = 20
_STATUS_FILTERS = ("active", "overdue", "paid", "archived")
_SORT_KEYS = (
    "due_date",
    "remaining",
    "amount",
    "interest",
    "created_at",
    "counterparty",
    "status",
)
_OPEN_STATUSES = frozenset({"active", "overdue"})


class DebtsPage(ft.Column):
    """Manage personal debts and loans."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._status_filter = "active"
        self._direction_filter = "all"
        self._sort_by = "due_date"
        self._alert_ids: set[str] = set()
        self._token = -1
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.debts", state.language),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.TUNE,
                            tooltip=tr("action.filters", state.language),
                            on_click=lambda _e: self._open_filters(),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            tooltip=tr("action.add", state.language),
                            on_click=lambda _e: self._open_editor(),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=self._list,
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        if state.debts_token != self._token:
            run_async(self._page, self.reload)

    def _open_filters(self) -> None:
        lang = self._state.language
        status_dd = ft.Dropdown(
            label=tr("debt.filter_status", lang),
            dense=True,
            value=self._status_filter,
            options=[
                ft.DropdownOption(
                    key=key,
                    text=tr(f"debt.filter.{key}", lang),
                )
                for key in _STATUS_FILTERS
            ],
        )
        direction_dd = ft.Dropdown(
            label=tr("debt.filter_direction", lang),
            dense=True,
            value=self._direction_filter,
            options=[
                ft.DropdownOption(
                    key="all",
                    text=tr("debt.filter_all_directions", lang),
                ),
                ft.DropdownOption(
                    key=DebtDirection.I_OWE.value,
                    text=tr("debt.i_owe", lang),
                ),
                ft.DropdownOption(
                    key=DebtDirection.OWED_TO_ME.value,
                    text=tr("debt.owed_to_me", lang),
                ),
            ],
        )
        sort_dd = ft.Dropdown(
            label=tr("debt.filter_sort", lang),
            dense=True,
            value=self._sort_by,
            options=[
                ft.DropdownOption(
                    key=key,
                    text=tr(f"debt.sort.{key}", lang),
                )
                for key in _SORT_KEYS
            ],
        )

        async def _apply() -> None:
            self._status_filter = str(status_dd.value or "active")
            self._direction_filter = str(direction_dd.value or "all")
            self._sort_by = str(sort_dd.value or "due_date")
            close()
            await self.reload()

        close = open_fullscreen_form(
            self._page,
            title=tr("action.filters", lang),
            lang=lang,
            overlay_key="debt_filters",
            body=[status_dd, direction_dd, sort_dd],
            on_save=_apply,
            save_label=tr("action.apply", lang, default=tr("action.save", lang)),
            save_icon=ft.Icons.CHECK,
        )

    async def reload(self) -> None:
        """Reload debts list for the current filters."""
        self._token = self._state.debts_token
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        self._alert_ids = pending_related_ids(
            self._state.container,
            self._state.settings,
            DEBT_ALERT_KINDS,
        )
        for related_id in list(self._alert_ids):
            mark_related_read(
                self._state.container, related_id, DEBT_ALERT_KINDS
            )
        if self._alert_ids:
            self._state.bump_refresh("dashboard")

        direction = (
            None
            if self._direction_filter in ("", "all", None)
            else self._direction_filter
        )
        try:
            debts = await self._state.container.list_debts.execute(
                status=self._status_filter,
                direction=direction,
                sort_by=self._sort_by,
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return

        if not debts:
            self._list.controls = [
                EmptyState(
                    tr("empty.debts", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            self._list.update()
            return

        cards: list[ft.Control] = []
        if self._status_filter in _OPEN_STATUSES:
            base = self._state.base_currency
            book = await load_rate_book(self._state.container)
            i_owe = Decimal("0")
            owed_to_me = Decimal("0")
            fx_ok = True
            for debt in debts:
                if debt.status not in (DebtStatus.ACTIVE, DebtStatus.OVERDUE):
                    continue
                converted = book.convert(
                    debt.remaining_amount,
                    debt.currency,
                    base,
                )
                if converted is None:
                    if debt.currency.upper() == base.upper():
                        converted = debt.remaining_amount
                    else:
                        fx_ok = False
                        continue
                if debt.direction == DebtDirection.I_OWE:
                    i_owe += converted
                else:
                    owed_to_me += converted
            if not fx_ok:
                snack(self._page, tr("fx.missing_rates", lang), error=True)
            cards.append(
                summary_strip(
                    [
                        (
                            tr("debts.total_i_owe", lang),
                            format_money(i_owe, base),
                            ft.Colors.ERROR,
                        ),
                        (
                            tr("debts.total_owed_to_me", lang),
                            format_money(owed_to_me, base),
                            ft.Colors.SECONDARY,
                        ),
                    ]
                )
            )
            cards.append(ft.Container(height=2))

        for debt in debts:
            interest = None
            if debt.interest_rate is not None:
                try:
                    interest = compute_debt_interest(debt).interest_amount
                except Exception:  # noqa: BLE001
                    interest = None
            can_repay = debt.status in (DebtStatus.ACTIVE, DebtStatus.OVERDUE)
            cards.append(
                DebtCard(
                    debt,
                    language=lang,
                    interest_amount=interest,
                    alert=debt.id in self._alert_ids,
                    on_click=self._open_detail,
                    on_edit=self._open_editor,
                    on_delete=self._confirm_delete,
                    on_repay=self._repay if can_repay else None,
                )
            )
        self._list.controls = cards
        self._list.update()

    def _confirm_delete(self, debt: Debt) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_debt.execute(debt.id)
            self._state.bump_refresh("dashboard")
            await self.reload()

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=debt.counterparty,
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _repay(self, debt: Debt) -> None:
        lang = self._state.language
        i_owe = debt.direction == DebtDirection.I_OWE
        has_interest = debt.interest_rate is not None

        async def _open() -> None:
            try:
                accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
                book = await load_rate_book(self._state.container)
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            if not accounts:
                snack(self._page, tr("error.no_accounts", lang), error=True)
                return

            convert_hint = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
            account_dd = ft.Dropdown(
                label=tr("field.account", lang),
                value=accounts[0].id,
                options=[
                    ft.DropdownOption(
                        key=a.id,
                        text=f"{a.name} · {format_money(a.balance, a.currency)}",
                    )
                    for a in accounts
                ],
            )

            principal_tf: Optional[ft.TextField] = None
            interest_tf: Optional[ft.TextField] = None
            amount_tf: Optional[ft.TextField] = None
            body: list[ft.Control]

            if has_interest:
                principal_tf = ft.TextField(
                    label=f"{tr('debt.principal_amount', lang)} ({debt.currency})",
                    value=str(debt.remaining_amount),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    autofocus=True,
                )
                interest_tf = ft.TextField(
                    label=f"{tr('debt.interest_amount', lang)} ({debt.currency})",
                    value="",
                    keyboard_type=ft.KeyboardType.NUMBER,
                )
                body = [account_dd, principal_tf, interest_tf, convert_hint]

                def _refresh_conversion(_e: ft.ControlEvent | None = None) -> None:
                    assert principal_tf is not None and interest_tf is not None
                    account = next(
                        (a for a in accounts if a.id == account_dd.value), accounts[0]
                    )
                    try:
                        principal = Decimal(
                            str(principal_tf.value or "0").replace(",", ".")
                        )
                        interest = Decimal(
                            str(interest_tf.value or "0").replace(",", ".")
                            if (interest_tf.value or "").strip()
                            else "0"
                        )
                    except (InvalidOperation, ValueError):
                        convert_hint.value = ""
                        convert_hint.update()
                        return
                    if principal < 0 or interest < 0 or (principal + interest) <= 0:
                        convert_hint.value = ""
                        convert_hint.update()
                        return
                    debt_total = principal + interest
                    converted = book.convert(
                        debt_total, debt.currency, account.currency
                    )
                    if converted is None:
                        convert_hint.value = tr(
                            "debt.no_rate",
                            lang,
                            pair=f"{debt.currency}/{account.currency}",
                        )
                        convert_hint.color = ft.Colors.ERROR
                    else:
                        convert_hint.value = format_money(converted, account.currency)
                        convert_hint.color = ft.Colors.ON_SURFACE_VARIANT
                    convert_hint.update()

                principal_tf.on_change = _refresh_conversion
                interest_tf.on_change = _refresh_conversion
                account_dd.on_select = _refresh_conversion
            else:
                amount_tf = ft.TextField(
                    label=tr("field.amount", lang),
                    value=str(debt.remaining_amount)
                    if accounts[0].currency.upper() == debt.currency.upper()
                    else "",
                    keyboard_type=ft.KeyboardType.NUMBER,
                    autofocus=True,
                )
                body = [account_dd, amount_tf, convert_hint]

                def _refresh_conversion(_e: ft.ControlEvent | None = None) -> None:
                    assert amount_tf is not None
                    account = next(
                        (a for a in accounts if a.id == account_dd.value), accounts[0]
                    )
                    try:
                        amount = Decimal(
                            str(amount_tf.value or "").replace(",", ".")
                        )
                    except (InvalidOperation, ValueError):
                        convert_hint.value = ""
                        convert_hint.update()
                        return
                    if amount <= 0:
                        convert_hint.value = ""
                        convert_hint.update()
                        return
                    converted = book.convert(amount, account.currency, debt.currency)
                    if converted is None:
                        convert_hint.value = tr(
                            "debt.no_rate",
                            lang,
                            pair=f"{account.currency}/{debt.currency}",
                        )
                        convert_hint.color = ft.Colors.ERROR
                    else:
                        convert_hint.value = tr(
                            "debt.converted_amount",
                            lang,
                            amount=format_money(converted, debt.currency),
                        )
                        convert_hint.color = ft.Colors.ON_SURFACE_VARIANT
                    convert_hint.update()

                amount_tf.on_change = _refresh_conversion
                account_dd.on_select = _refresh_conversion

            async def _save() -> None:
                account_id = account_dd.value or accounts[0].id
                account = next(
                    (a for a in accounts if a.id == account_id), accounts[0]
                )
                interest_amount: Optional[Decimal] = None

                if has_interest:
                    assert principal_tf is not None and interest_tf is not None
                    try:
                        principal = Decimal(
                            str(principal_tf.value or "").replace(",", ".")
                        )
                        interest_raw = (interest_tf.value or "").strip()
                        interest_amount = (
                            Decimal(interest_raw.replace(",", "."))
                            if interest_raw
                            else Decimal("0")
                        )
                        if principal < 0 or interest_amount < 0:
                            raise InvalidOperation
                        debt_total = principal + interest_amount
                        if debt_total <= 0:
                            raise InvalidOperation
                    except (InvalidOperation, ValueError):
                        snack(self._page, tr("invalid_amount", lang), error=True)
                        return
                    pay_amount = book.convert(
                        debt_total, debt.currency, account.currency
                    )
                    if pay_amount is None:
                        snack(
                            self._page,
                            tr(
                                "debt.no_rate",
                                lang,
                                pair=f"{debt.currency}/{account.currency}",
                            ),
                            error=True,
                        )
                        return
                    if interest_amount <= 0:
                        interest_amount = None
                else:
                    assert amount_tf is not None
                    try:
                        pay_amount = Decimal(
                            str(amount_tf.value or "").replace(",", ".")
                        )
                        if pay_amount <= 0:
                            raise InvalidOperation
                    except (InvalidOperation, ValueError):
                        snack(self._page, tr("invalid_amount", lang), error=True)
                        return
                    converted = book.convert(
                        pay_amount, account.currency, debt.currency
                    )
                    if converted is None:
                        snack(
                            self._page,
                            tr(
                                "debt.no_rate",
                                lang,
                                pair=f"{account.currency}/{debt.currency}",
                            ),
                            error=True,
                        )
                        return

                if i_owe and pay_amount > account.balance:
                    snack(self._page, tr("error.insufficient_funds", lang), error=True)
                    return
                try:
                    await self._state.container.repay_debt.execute(
                        debt.id,
                        pay_amount,
                        account_id=account_id,
                        interest_amount=interest_amount,
                    )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                close()
                self._state.bump_refresh("dashboard", "accounts", "transactions", "debts")
                await self.reload()
                snack(self._page, tr("action.saved", lang))

            close = open_fullscreen_form(
                self._page,
                title=(
                    f"{tr('debt.repay' if i_owe else 'debt.receive', lang)}"
                    f" · {debt.counterparty}"
                ),
                lang=lang,
                overlay_key="debt_repay",
                body=body,
                on_save=_save,
                save_icon=ft.Icons.PAYMENTS_OUTLINED,
            )

        run_async(self._page, _open)

    def _open_detail(self, debt: Debt) -> None:
        lang = self._state.language
        body = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        close_holder: dict[str, object] = {}

        def _close_detail() -> None:
            closer = close_holder.get("close")
            if callable(closer):
                closer()

        async def _load() -> None:
            body.controls = [loading_indicator()]
            try:
                body.update()
            except Exception:  # noqa: BLE001
                pass
            try:
                fresh = await self._state.container.debt_repository.get_by_id(debt.id)
                debt_obj = fresh or debt
                projection = await self._state.container.get_debt_projection.execute(
                    debt_obj.id
                )
                accounts = {
                    a.id: a
                    for a in await self._state.container.list_accounts.execute(
                        active_only=False
                    )
                }
                txs = await self._state.container.list_transactions.execute(
                    debt_id=debt_obj.id,
                    limit=_PAYMENT_PAGE + 1,
                    offset=0,
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return

            has_more = len(txs) > _PAYMENT_PAGE
            shown = txs[:_PAYMENT_PAGE]
            offset = {"n": len(shown)}

            proj_rows: list[ft.Control] = [
                ft.Text(tr("debt.projection", lang), weight=ft.FontWeight.W_700),
            ]
            if projection.recommended_monthly_payment is not None:
                proj_rows.append(
                    ft.Text(
                        f"{tr('debt.recommended_monthly', lang)}: "
                        f"{format_money(projection.recommended_monthly_payment, debt_obj.currency)}"
                    )
                )
            if projection.projected_payoff_date is not None:
                proj_rows.append(
                    ft.Text(
                        f"{tr('debt.projected_date', lang)}: "
                        f"{format_date(projection.projected_payoff_date)}"
                    )
                )
            if projection.is_on_track is True:
                proj_rows.append(
                    ft.Text(tr("debt.on_track", lang), color=ft.Colors.PRIMARY)
                )
            elif projection.is_on_track is False:
                proj_rows.append(
                    ft.Text(tr("debt.off_track", lang), color=ft.Colors.ERROR)
                )

            payments_col = ft.Column(spacing=8, tight=True)
            payments_col.controls = [
                ft.Text(tr("debt.payments", lang), weight=ft.FontWeight.W_700),
            ]
            if not shown:
                payments_col.controls.append(muted_text("—"))
            else:
                for tx in shown:
                    payments_col.controls.append(
                        self._payment_row(debt_obj, tx, accounts, close_holder)
                    )

            async def _more(_e: ft.ControlEvent | None = None) -> None:
                more = await self._state.container.list_transactions.execute(
                    debt_id=debt_obj.id,
                    limit=_PAYMENT_PAGE + 1,
                    offset=offset["n"],
                )
                more_has = len(more) > _PAYMENT_PAGE
                chunk = more[:_PAYMENT_PAGE]
                offset["n"] += len(chunk)
                for tx in chunk:
                    payments_col.controls.append(
                        self._payment_row(debt_obj, tx, accounts, close_holder)
                    )
                load_more_btn.visible = more_has
                payments_col.update()
                load_more_btn.update()

            load_more_btn = ft.TextButton(
                tr("action.load_more", lang, default="Load more"),
                visible=has_more,
                on_click=lambda e: run_async(self._page, _more, e),
            )

            async def _do_archive(_e: ft.ControlEvent | None = None) -> None:
                await self._archive(debt_obj, close_holder)

            def _edit(_e: ft.ControlEvent | None = None) -> None:
                _close_detail()
                self._open_editor(debt_obj)

            def _repay_action(_e: ft.ControlEvent | None = None) -> None:
                _close_detail()
                self._repay(debt_obj)

            actions: list[ft.Control] = []
            if debt_obj.status in (DebtStatus.ACTIVE, DebtStatus.OVERDUE):
                actions.append(
                    ft.FilledButton(
                        tr(
                            "debt.repay"
                            if debt_obj.direction == DebtDirection.I_OWE
                            else "debt.receive",
                            lang,
                        ),
                        icon=ft.Icons.PAYMENTS_OUTLINED,
                        on_click=_repay_action,
                    )
                )
            actions.append(
                ft.FilledTonalButton(
                    tr("action.edit", lang),
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=_edit,
                )
            )
            if debt_obj.status == DebtStatus.PAID:
                actions.append(
                    ft.OutlinedButton(
                        tr("debt.archive", lang),
                        icon=ft.Icons.ARCHIVE_OUTLINED,
                        on_click=lambda e: run_async(self._page, _do_archive, e),
                    )
                )

            interest = None
            if debt_obj.interest_rate is not None:
                try:
                    result = await self._state.container.calculate_debt_interest.execute(
                        debt_obj.id
                    )
                    interest = result.interest_amount
                except Exception:  # noqa: BLE001
                    interest = None

            body.controls = [
                DebtCard(
                    debt_obj,
                    language=lang,
                    interest_amount=interest,
                ),
                card_surface(ft.Column(proj_rows, spacing=6, tight=True)),
                ft.Row(wrap=True, spacing=8, controls=actions),
                payments_col,
                load_more_btn,
            ]
            body.update()

        close = open_fullscreen_form(
            self._page,
            title=debt.counterparty,
            lang=lang,
            overlay_key="debt_detail",
            body=[body],
            on_save=None,
            show_save=False,
        )
        close_holder["close"] = close
        run_async(self._page, _load)

    def _payment_row(
        self,
        debt: Debt,
        tx: object,
        accounts: dict,
        close_holder: dict,
    ) -> ft.Control:
        lang = self._state.language
        credit = debt_credit_amount(tx)  # type: ignore[arg-type]
        account = accounts.get(getattr(tx, "account_id", ""))
        account_name = account.name if account is not None else "—"
        comment = (getattr(tx, "comment", "") or "").strip()
        date_txt = format_date(getattr(tx, "date", None))

        def _delete(_e: ft.ControlEvent | None = None) -> None:
            async def _do() -> None:
                try:
                    await self._state.container.delete_debt_payment.execute(
                        getattr(tx, "id"),
                        debt_id=debt.id,
                    )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                self._state.bump_refresh(
                    "dashboard", "accounts", "transactions", "debts"
                )
                closer = close_holder.get("close")
                if callable(closer):
                    closer()
                await self.reload()
                refreshed = await self._state.container.debt_repository.get_by_id(
                    debt.id
                )
                if refreshed is not None:
                    self._open_detail(refreshed)
                snack(self._page, tr("action.saved", lang))

            confirm_dialog(
                self._page,
                title=tr("action.confirm_delete", lang),
                message=format_money(credit, debt.currency),
                confirm_text=tr("action.delete", lang),
                cancel_text=tr("action.cancel", lang),
                on_confirm=_do,
            )

        return card_surface(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                f"{date_txt} · {format_money(credit, debt.currency)}",
                                weight=ft.FontWeight.W_600,
                            ),
                            muted_text(account_name),
                            muted_text(tr("debt.payment_type", lang)),
                            muted_text(comment) if comment else ft.Container(height=0),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.ERROR,
                        on_click=_delete,
                    ),
                ],
            )
        )

    async def _archive(self, debt: Debt, close_holder: dict) -> None:
        try:
            await self._state.container.archive_debt.execute(debt.id)
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return
        closer = close_holder.get("close")
        if callable(closer):
            closer()
        self._state.bump_refresh("dashboard")
        await self.reload()
        snack(self._page, tr("action.saved", self._state.language))

    def _open_editor(self, debt: Optional[Debt] = None) -> None:
        lang = self._state.language

        async def _open() -> None:
            accounts: list = []
            try:
                accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
            except Exception:  # noqa: BLE001
                accounts = []

            name_tf = ft.TextField(
                label=tr("field.name", lang),
                value=debt.counterparty if debt else "",
            )
            amount_tf = ft.TextField(
                label=tr("field.amount", lang),
                value=str(debt.amount) if debt else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            currency_picker = CurrencyTickerPicker(
                self._page,
                lang=lang,
                label=tr("field.currency", lang),
                value=debt.currency if debt else self._state.base_currency,
                include_crypto=True,
                expand=True,
            )
            direction_dd = ft.Dropdown(
                label=tr("field.direction", lang),
                value=(
                    debt.direction.value
                    if debt
                    else DebtDirection.I_OWE.value
                ),
                options=[
                    ft.DropdownOption(
                        key=DebtDirection.I_OWE.value,
                        text=tr("debt.i_owe", lang),
                    ),
                    ft.DropdownOption(
                        key=DebtDirection.OWED_TO_ME.value,
                        text=tr("debt.owed_to_me", lang),
                    ),
                ],
            )
            rate_tf = ft.TextField(
                label=tr("field.interest", lang),
                value=str(debt.interest_rate)
                if debt and debt.interest_rate is not None
                else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            due_field = DateTimeField(
                self._page,
                lang=lang,
                label=tr("field.date", lang),
                value=debt.due_date if debt and debt.due_date else None,
                allow_clear=True,
            )
            comment_tf = ft.TextField(
                label=tr("field.comment", lang),
                value=debt.comment if debt else "",
            )

            controls: list[ft.Control] = [
                name_tf,
                amount_tf,
                currency_picker,
                direction_dd,
            ]
            account_dd: Optional[ft.Dropdown] = None
            record_cash = ft.Checkbox(
                label=tr("debt.record_cash", lang),
                value=True,
            )
            if debt is None and accounts:
                account_dd = ft.Dropdown(
                    label=tr("field.account", lang),
                    value=accounts[0].id,
                    options=[
                        ft.DropdownOption(
                            key=a.id,
                            text=f"{a.name} · {format_money(a.balance, a.currency)}",
                        )
                        for a in accounts
                    ],
                )
                controls.extend([record_cash, account_dd])
            elif debt is not None:
                controls.append(
                    ft.Text(
                        f"{tr('field.remaining', lang)}: "
                        f"{format_money(debt.remaining_amount, debt.currency)}",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                )
            controls.extend([rate_tf, due_field, comment_tf])

            async def _save() -> None:
                try:
                    amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                    if amount <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
                rate = None
                if (rate_tf.value or "").strip():
                    rate = Decimal(str(rate_tf.value).replace(",", "."))
                due = due_field.value
                entity = Debt(
                    id=debt.id
                    if debt
                    else Debt(
                        counterparty="tmp",
                        amount=1,
                        remaining_amount=1,
                        direction=DebtDirection.I_OWE,
                    ).id,
                    counterparty=(name_tf.value or "").strip() or "—",
                    amount=amount,
                    remaining_amount=debt.remaining_amount if debt else amount,
                    currency=(currency_picker.value or "RUB").upper(),
                    direction=DebtDirection(direction_dd.value),
                    status=debt.status if debt else DebtStatus.ACTIVE,
                    interest_rate=rate,
                    due_date=due,
                    started_at=debt.started_at if debt else datetime.now(timezone.utc),
                    comment=comment_tf.value or "",
                    created_at=debt.created_at if debt else datetime.now(timezone.utc),
                )
                try:
                    if debt:
                        await self._state.container.update_debt.execute(entity)
                    else:
                        account_id = None
                        if (
                            record_cash.value
                            and account_dd is not None
                            and account_dd.value
                        ):
                            account_id = account_dd.value
                            account = next(
                                (a for a in accounts if a.id == account_id), None
                            )
                            if account is not None:
                                # Cash movement is in account currency — keep debt in sync.
                                entity.currency = account.currency.upper()
                            if (
                                account is not None
                                and entity.direction == DebtDirection.OWED_TO_ME
                                and amount > account.balance
                            ):
                                snack(
                                    self._page,
                                    tr("error.insufficient_funds", lang),
                                    error=True,
                                )
                                return
                        await self._state.container.create_debt.execute(
                            entity,
                            account_id=account_id,
                        )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                close()
                self._state.bump_refresh("dashboard", "accounts", "transactions", "debts")
                await self.reload()
                snack(self._page, tr("action.saved", lang))

            close = open_fullscreen_form(
                self._page,
                title=tr("action.edit", lang) if debt else tr("action.add", lang),
                lang=lang,
                overlay_key="debt_editor",
                body=controls,
                on_save=_save,
            )

        run_async(self._page, _open)
