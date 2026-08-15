"""Subscriptions page with upcoming charges, detail history, and CRUD."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.subscription import (
    Periodicity,
    Subscription,
    SubscriptionStatus,
)
from lib.domain.use_cases.subscriptions import monthly_equivalent
from lib.presentation.notification_badges import (
    SUBSCRIPTION_ALERT_KINDS,
    mark_related_read,
    pending_related_ids,
)
from lib.presentation.styles import card_surface, muted_text, page_header, summary_strip
from lib.presentation.utils import (
    format_date,
    format_money,
    load_rate_book,
    run_async,
    snack,
    tr,
)
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.subscription_card import (
    SubscriptionCard,
    periodicity_label,
)

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_CHARGE_PAGE = 20

_PERIOD_OPTIONS = (
    Periodicity.DAILY,
    Periodicity.WEEKLY,
    Periodicity.BIWEEKLY,
    Periodicity.MONTHLY,
    Periodicity.QUARTERLY,
    Periodicity.SEMI_ANNUAL,
    Periodicity.YEARLY,
    Periodicity.CUSTOM,
)


class SubscriptionsPage(ft.Column):
    """List subscriptions and upcoming billing dates."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._accounts: list = []
        self._calendar = ft.Column(spacing=6)
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._alert_ids: set[str] = set()
        self._token = -1
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.subscriptions", state.language),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            on_click=lambda _e: self._open_editor(),
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(
                                tr("subscriptions.calendar", state.language),
                                weight=ft.FontWeight.W_600,
                            ),
                            self._calendar,
                        ],
                    ),
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
        if state.subscriptions_token != self._token:
            run_async(self._page, self.reload)

    async def reload(self) -> None:
        """Reload subscriptions and build upcoming calendar."""
        self._token = self._state.subscriptions_token
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        self._alert_ids = pending_related_ids(
            self._state.container,
            self._state.settings,
            SUBSCRIPTION_ALERT_KINDS,
        )
        for related_id in list(self._alert_ids):
            mark_related_read(
                self._state.container, related_id, SUBSCRIPTION_ALERT_KINDS
            )
        if self._alert_ids:
            self._state.bump_refresh("dashboard")
        try:
            self._accounts = await self._state.container.list_accounts.execute(
                active_only=True
            )
            items = await self._state.container.list_subscriptions.execute()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return

        upcoming = sorted(
            [s for s in items if s.status == SubscriptionStatus.ACTIVE],
            key=lambda s: s.next_billing_date,
        )[:8]
        if upcoming:
            self._calendar.controls = [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.EVENT, color=ft.Colors.TEAL_700),
                    title=ft.Text(s.name),
                    subtitle=ft.Text(format_date(s.next_billing_date)),
                    trailing=ft.Text(
                        format_money(s.amount, s.currency),
                        weight=ft.FontWeight.W_600,
                    ),
                )
                for s in upcoming
            ]
        else:
            self._calendar.controls = [
                ft.Text("—", color=ft.Colors.ON_SURFACE_VARIANT)
            ]
        self._calendar.update()

        if not items:
            self._list.controls = [
                EmptyState(
                    tr("empty.subscriptions", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            self._list.update()
            return

        base = self._state.base_currency
        book = await load_rate_book(self._state.container)
        monthly = Decimal("0")
        yearly = Decimal("0")
        fx_ok = True
        for sub in items:
            if sub.status != SubscriptionStatus.ACTIVE:
                continue
            monthly_amt = monthly_equivalent(
                sub.amount,
                sub.periodicity,
                custom_interval_days=sub.custom_interval_days,
            )
            converted = book.convert(monthly_amt, sub.currency, base)
            if converted is None:
                if sub.currency.upper() == base.upper():
                    converted = monthly_amt
                else:
                    fx_ok = False
                    continue
            monthly += converted
            yearly += converted * Decimal("12")
        if not fx_ok:
            snack(self._page, tr("fx.missing_rates", lang), error=True)

        self._list.controls = [
            summary_strip(
                [
                    (
                        tr("subscriptions.monthly_total", lang),
                        format_money(monthly, base),
                        ft.Colors.PRIMARY,
                    ),
                    (
                        tr("subscriptions.yearly_total", lang),
                        format_money(yearly, base),
                        ft.Colors.SECONDARY,
                    ),
                ]
            ),
            *[
                SubscriptionCard(
                    s,
                    language=lang,
                    alert=s.id in self._alert_ids,
                    on_open=self._open_detail,
                    on_edit=self._open_editor,
                    on_delete=self._confirm_delete,
                )
                for s in items
            ],
        ]
        self._list.update()

    def _confirm_delete(self, sub: Subscription) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_subscription.execute(sub.id)
            self._state.bump_refresh("dashboard", "subscriptions")
            await self.reload()

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=sub.name,
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _open_detail(self, sub: Subscription) -> None:
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
                fresh = await self._state.container.subscription_repository.get_by_id(
                    sub.id
                )
                sub_obj = fresh or sub
                accounts = {
                    a.id: a
                    for a in await self._state.container.list_accounts.execute(
                        active_only=False
                    )
                }
                txs = await self._state.container.list_transactions.execute(
                    subscription_id=sub_obj.id,
                    limit=_CHARGE_PAGE + 1,
                    offset=0,
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return

            has_more = len(txs) > _CHARGE_PAGE
            shown = txs[:_CHARGE_PAGE]
            offset = {"n": len(shown)}

            charges_col = ft.Column(spacing=8, tight=True)
            charges_col.controls = [
                ft.Text(
                    tr("subscription.charge_history", lang),
                    weight=ft.FontWeight.W_700,
                ),
            ]
            if not shown:
                charges_col.controls.append(muted_text("—"))
            else:
                for idx, tx in enumerate(shown):
                    charges_col.controls.append(
                        self._charge_row(
                            sub_obj,
                            tx,
                            accounts,
                            close_holder,
                            is_latest=idx == 0,
                        )
                    )

            async def _more(_e: ft.ControlEvent | None = None) -> None:
                more = await self._state.container.list_transactions.execute(
                    subscription_id=sub_obj.id,
                    limit=_CHARGE_PAGE + 1,
                    offset=offset["n"],
                )
                more_has = len(more) > _CHARGE_PAGE
                chunk = more[:_CHARGE_PAGE]
                offset["n"] += len(chunk)
                for tx in chunk:
                    charges_col.controls.append(
                        self._charge_row(
                            sub_obj, tx, accounts, close_holder, is_latest=False
                        )
                    )
                load_more_btn.visible = more_has
                charges_col.update()
                load_more_btn.update()

            load_more_btn = ft.TextButton(
                tr("action.load_more", lang),
                visible=has_more,
                on_click=lambda e: run_async(self._page, _more, e),
            )

            async def _pause(_e: ft.ControlEvent | None = None) -> None:
                await self._state.container.pause_subscription.execute(sub_obj.id)
                self._state.bump_refresh("subscriptions")
                await _load()
                await self.reload()

            async def _resume(_e: ft.ControlEvent | None = None) -> None:
                await self._state.container.resume_subscription.execute(sub_obj.id)
                self._state.bump_refresh("subscriptions")
                await _load()
                await self.reload()

            async def _charge(_e: ft.ControlEvent | None = None) -> None:
                try:
                    await self._state.container.charge_subscription_now.execute(
                        sub_obj.id,
                        check_balance=False,
                    )
                except ValueError as exc:
                    if str(exc) == "insufficient_funds":
                        snack(
                            self._page,
                            tr("subscription.insufficient_funds", lang),
                            error=True,
                        )
                        return
                    snack(self._page, str(exc), error=True)
                    return
                self._state.bump_refresh("dashboard", "subscriptions")
                snack(self._page, tr("action.saved", lang))
                await _load()
                await self.reload()

            def _edit(_e: ft.ControlEvent | None = None) -> None:
                _close_detail()
                self._open_editor(sub_obj)

            actions: list[ft.Control] = [
                ft.FilledButton(
                    tr("subscription.charge_now", lang),
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    on_click=lambda e: run_async(self._page, _charge, e),
                ),
                ft.FilledTonalButton(
                    tr("action.edit", lang),
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=_edit,
                ),
            ]
            auto_sw = ft.Switch(
                label=tr("subscription.auto_charge", lang),
                value=bool(sub_obj.auto_charge),
            )
            sub_holder = {"sub": sub_obj}

            async def _toggle_auto(_e: ft.ControlEvent | None = None) -> None:
                current = sub_holder["sub"]
                updated = await self._state.container.update_subscription.execute(
                    current.model_copy(update={"auto_charge": bool(auto_sw.value)})
                )
                sub_holder["sub"] = updated
                self._state.bump_refresh("subscriptions")
                snack(self._page, tr("action.saved", lang))

            auto_sw.on_change = lambda e: run_async(self._page, _toggle_auto, e)
            if sub_obj.status == SubscriptionStatus.ACTIVE:
                actions.append(
                    ft.OutlinedButton(
                        tr("subscription.pause", lang),
                        icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                        on_click=lambda e: run_async(self._page, _pause, e),
                    )
                )
            elif sub_obj.status == SubscriptionStatus.PAUSED:
                actions.append(
                    ft.OutlinedButton(
                        tr("subscription.resume", lang),
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                        on_click=lambda e: run_async(self._page, _resume, e),
                    )
                )

            meta = ft.Column(
                spacing=4,
                tight=True,
                controls=[
                    ft.Text(
                        periodicity_label(
                            sub_obj.periodicity,
                            lang,
                            custom_interval_days=sub_obj.custom_interval_days,
                        )
                    ),
                    ft.Text(
                        tr(
                            "subscription.next_billing",
                            lang,
                            date=format_date(sub_obj.next_billing_date),
                        )
                    ),
                    ft.Text(
                        f"{tr('subscription.start_date', lang)}: "
                        f"{sub_obj.start_date.isoformat()}"
                    ),
                    ft.Text(
                        f"{tr('subscription.end_date', lang)}: "
                        f"{sub_obj.end_date.isoformat() if sub_obj.end_date else '—'}"
                    ),
                    ft.Text(
                        f"{tr('subscription.max_payments', lang)}: "
                        f"{sub_obj.max_payments if sub_obj.max_payments is not None else '—'} "
                        f"({sub_obj.payments_made})"
                    ),
                    auto_sw,
                ],
            )

            body.controls = [
                SubscriptionCard(sub_obj, language=lang),
                card_surface(meta),
                ft.Row(wrap=True, spacing=8, controls=actions),
                charges_col,
                load_more_btn,
            ]
            body.update()

        close = open_fullscreen_form(
            self._page,
            title=sub.name,
            lang=lang,
            overlay_key="subscription_detail",
            body=[body],
            on_save=None,
            show_save=False,
        )
        close_holder["close"] = close
        run_async(self._page, _load)

    def _charge_row(
        self,
        sub: Subscription,
        tx,
        accounts: dict,
        close_holder: dict,
        *,
        is_latest: bool,
    ) -> ft.Control:
        lang = self._state.language
        account = accounts.get(tx.account_id)
        account_name = account.name if account else tx.account_id
        subtitle = account_name
        if tx.comment:
            subtitle = f"{account_name} · {tx.comment}"

        async def _delete(_e: ft.ControlEvent | None = None) -> None:
            confirm_dialog(
                self._page,
                title=tr("action.confirm_delete", lang),
                message=tr("subscription.delete_charge_hint", lang),
                confirm_text=tr("action.delete", lang),
                cancel_text=tr("action.cancel", lang),
                on_confirm=lambda: run_async(self._page, _do_delete),
            )

        async def _do_delete() -> None:
            await self._state.container.delete_subscription_charge.execute(
                tx.id, subscription_id=sub.id
            )
            self._state.bump_refresh("subscriptions")
            closer = close_holder.get("close")
            if callable(closer):
                closer()
            await self.reload()
            self._open_detail(sub)

        trailing: list[ft.Control] = [
            ft.Text(format_money(tx.amount, tx.currency), weight=ft.FontWeight.W_600)
        ]
        if is_latest:
            trailing.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.ERROR,
                    on_click=lambda e: run_async(self._page, _delete, e),
                )
            )
        return card_surface(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(format_date(tx.date), weight=ft.FontWeight.W_600),
                            muted_text(subtitle),
                        ],
                    ),
                    ft.Row(spacing=4, tight=True, controls=trailing),
                ],
            )
        )

    def _open_editor(self, sub: Optional[Subscription] = None) -> None:
        run_async(self._page, self._open_editor_async, sub)

    async def _open_editor_async(self, sub: Optional[Subscription] = None) -> None:
        lang = self._state.language
        if not self._accounts:
            try:
                self._accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
        if not self._accounts:
            snack(self._page, tr("empty.accounts", lang), error=True)
            return

        cat_names: list[str] = [tr("category.other", lang)]
        if self._state.container.list_categories is not None:
            cats = await self._state.container.list_categories.execute()
            if cats:
                cat_names = [c.name for c in cats]

        name_tf = ft.TextField(
            label=tr("field.name", lang), value=sub.name if sub else ""
        )
        amount_tf = ft.TextField(
            label=tr("field.amount", lang),
            value=str(sub.amount) if sub else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        account_dd = ft.Dropdown(
            label=tr("field.account", lang),
            value=sub.account_id if sub else self._accounts[0].id,
            options=[
                ft.DropdownOption(key=a.id, text=a.name) for a in self._accounts
            ],
        )
        category_dd = ft.Dropdown(
            label=tr("field.category", lang),
            value=sub.category if sub else cat_names[0],
            options=[ft.DropdownOption(key=c, text=c) for c in cat_names],
        )
        period_dd = ft.Dropdown(
            label=tr("field.period", lang),
            value=(sub.periodicity.value if sub else Periodicity.MONTHLY.value),
            options=[
                ft.DropdownOption(
                    key=p.value,
                    text=periodicity_label(p, lang),
                )
                for p in _PERIOD_OPTIONS
            ],
        )
        custom_tf = ft.TextField(
            label=tr("subscription.custom_interval", lang),
            value=(
                str(sub.custom_interval_days)
                if sub and sub.custom_interval_days
                else ""
            ),
            keyboard_type=ft.KeyboardType.NUMBER,
            visible=(sub.periodicity == Periodicity.CUSTOM) if sub else False,
        )
        start_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("subscription.start_date", lang),
            value=(
                datetime.combine(
                    sub.start_date, datetime.min.time(), tzinfo=timezone.utc
                )
                if sub
                else datetime.now(timezone.utc)
            ),
        )
        end_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("subscription.end_date", lang),
            value=(
                datetime.combine(
                    sub.end_date, datetime.min.time(), tzinfo=timezone.utc
                )
                if sub and sub.end_date
                else None
            ),
        )
        max_payments_tf = ft.TextField(
            label=tr("subscription.max_payments", lang),
            value=(
                str(sub.max_payments) if sub and sub.max_payments is not None else ""
            ),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        next_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("field.date", lang),
            value=(sub.next_billing_date if sub else datetime.now(timezone.utc)),
        )
        status_dd = ft.Dropdown(
            label=tr("field.active", lang),
            value=(sub.status.value if sub else SubscriptionStatus.ACTIVE.value),
            options=[
                ft.DropdownOption(
                    key=s.value,
                    text=tr(f"subscription.status.{s.value}", lang),
                )
                for s in (
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PAUSED,
                    SubscriptionStatus.CANCELLED,
                )
            ],
        )
        auto_sw = ft.Switch(
            label=tr("subscription.auto_charge", lang),
            value=bool(sub.auto_charge) if sub else True,
        )

        def _on_period(_e: ft.ControlEvent) -> None:
            custom_tf.visible = period_dd.value == Periodicity.CUSTOM.value
            try:
                custom_tf.update()
            except Exception:  # noqa: BLE001
                pass

        period_dd.on_select = _on_period

        close_holder: dict[str, object] = {}

        async def _save(_e: ft.ControlEvent | None = None) -> None:
            try:
                amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                if amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                snack(self._page, tr("invalid_amount", lang), error=True)
                return
            next_date = next_field.value
            start_dt = start_field.value
            if next_date is None or start_dt is None:
                snack(self._page, tr("invalid_date", lang), error=True)
                return
            start = start_dt.date() if isinstance(start_dt, datetime) else start_dt
            end_dt = end_field.value
            end: Optional[date] = None
            if end_dt is not None:
                end = end_dt.date() if isinstance(end_dt, datetime) else end_dt
            custom_days = None
            periodicity = Periodicity(period_dd.value)
            if periodicity == Periodicity.CUSTOM:
                try:
                    custom_days = int(custom_tf.value or "0")
                    if custom_days < 1:
                        raise ValueError
                except ValueError:
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
            max_payments = None
            raw_max = (max_payments_tf.value or "").strip()
            if raw_max:
                try:
                    max_payments = int(raw_max)
                    if max_payments < 1:
                        raise ValueError
                except ValueError:
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
            account = next(
                (a for a in self._accounts if a.id == account_dd.value),
                self._accounts[0],
            )
            status = SubscriptionStatus(
                status_dd.value or SubscriptionStatus.ACTIVE.value
            )
            entity = Subscription(
                id=(
                    sub.id
                    if sub
                    else Subscription(
                        name="tmp",
                        amount=1,
                        account_id=account.id,
                        next_billing_date=next_date,
                    ).id
                ),
                name=(name_tf.value or "").strip() or "Subscription",
                amount=amount,
                currency=account.currency,
                account_id=account.id,
                category=category_dd.value or cat_names[0],
                periodicity=periodicity,
                custom_interval_days=custom_days,
                start_date=start,
                end_date=end,
                max_payments=max_payments,
                payments_made=sub.payments_made if sub else 0,
                next_billing_date=next_date,
                status=status,
                auto_charge=bool(auto_sw.value),
                last_charged_at=sub.last_charged_at if sub else None,
                last_skip_date=sub.last_skip_date if sub else None,
                comment=sub.comment if sub else "",
                created_at=sub.created_at if sub else datetime.now(timezone.utc),
            )
            if sub:
                await self._state.container.update_subscription.execute(entity)
            else:
                await self._state.container.create_subscription.execute(entity)
            closer = close_holder.get("close")
            if callable(closer):
                closer()
            self._state.bump_refresh("dashboard", "subscriptions")
            await self.reload()
            snack(self._page, tr("action.saved", lang))

        body = ft.Column(
            tight=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                name_tf,
                amount_tf,
                account_dd,
                category_dd,
                period_dd,
                custom_tf,
                start_field,
                end_field,
                max_payments_tf,
                next_field,
                status_dd,
                auto_sw,
            ],
        )
        close = open_fullscreen_form(
            self._page,
            title=tr("action.edit", lang) if sub else tr("action.add", lang),
            lang=lang,
            overlay_key="subscription_editor",
            body=[body],
            on_save=_save,
        )
        close_holder["close"] = close
