"""Settings page: theme, language, currency, export, backup, PIN."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Sequence

import flet as ft

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.settings import AppSettings
from lib.domain.use_cases.align_currencies import align_sole_account_currency
from lib.infrastructure.services.backup_service import BackupService
from lib.infrastructure.services.biometric import BiometricStatus
from lib.infrastructure.services.data_reset_service import DataResetService
from lib.infrastructure.services.encryption_service import EncryptionService
from lib.infrastructure.services.export_service import ExportService
from lib.infrastructure.services.reminder_scheduler import schedule_reminders
from lib.infrastructure.services.localization import normalize_lang
from lib.infrastructure.services.push_notifier import request_push_permissions
from lib.presentation.styles import card_surface, page_header, section_title
from lib.presentation.theme import apply_theme
from lib.presentation.utils import run_async, snack, tr
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.currency_ticker_picker import CurrencyTickerPicker

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _settings_section(
    title: str,
    icon: ft.IconData,
    controls: Sequence[ft.Control],
    *,
    expanded: bool = False,
    on_toggle: Optional[Callable[[ft.Container, bool], None]] = None,
) -> ft.Container:
    """Expandable card block with icon title (accordion-friendly)."""
    body = ft.Column(
        spacing=12,
        tight=True,
        visible=expanded,
        controls=list(controls),
    )
    chevron = ft.Icon(
        ft.Icons.EXPAND_LESS if expanded else ft.Icons.EXPAND_MORE,
        size=22,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    def _apply(open_: bool) -> None:
        body.visible = open_
        chevron.icon = ft.Icons.EXPAND_LESS if open_ else ft.Icons.EXPAND_MORE
        try:
            body.update()
            chevron.update()
        except Exception:  # noqa: BLE001
            pass

    def _toggle(_e: ft.ControlEvent | None = None) -> None:
        will_open = not body.visible
        if on_toggle is not None:
            on_toggle(section, will_open)
        else:
            _apply(will_open)

    header = ft.Container(
        ink=True,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=2, vertical=2),
        on_click=_toggle,
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=34,
                    height=34,
                    border_radius=10,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        icon,
                        size=18,
                        color=ft.Colors.ON_PRIMARY_CONTAINER,
                    ),
                ),
                ft.Container(expand=True, content=section_title(title)),
                chevron,
            ],
        ),
    )
    section = card_surface(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[header, body],
        ),
        padding=16,
    )
    section.data = {"apply": _apply, "body": body}
    return section


class SettingsPage(ft.Column):
    """Application preferences and data tools, grouped by section."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._sections: list[ft.Container] = []

        s = state.settings
        lang = state.language

        def _accordion(section: ft.Container, will_open: bool) -> None:
            for item in self._sections:
                apply = (getattr(item, "data", None) or {}).get("apply")
                if callable(apply):
                    apply(item is section and will_open)

        def section(
            title: str,
            icon: ft.IconData,
            controls: Sequence[ft.Control],
            *,
            expanded: bool = False,
        ) -> ft.Container:
            block = _settings_section(
                title,
                icon,
                controls,
                expanded=expanded,
                on_toggle=_accordion,
            )
            self._sections.append(block)
            return block

        self._currency = CurrencyTickerPicker(
            page,
            lang=lang,
            label=tr("settings.default_currency", lang),
            value=normalize_currency_code(s.default_currency),
            include_crypto=True,
            expand=True,
        )
        self._theme = ft.Dropdown(
            label=tr("settings.theme", lang),
            value=s.theme,
            options=[
                ft.DropdownOption(key="light", text=tr("settings.theme.light", lang)),
                ft.DropdownOption(key="dark", text=tr("settings.theme.dark", lang)),
                ft.DropdownOption(key="system", text=tr("settings.theme.system", lang)),
            ],
            expand=True,
            dense=True,
        )
        self._language = ft.Dropdown(
            label=tr("settings.language", lang),
            value=normalize_lang(s.language),
            options=[
                ft.DropdownOption(key="ru", text=tr("lang.ru", lang)),
                ft.DropdownOption(key="en", text=tr("lang.en", lang)),
                ft.DropdownOption(key="uz", text=tr("lang.uz", lang)),
            ],
            expand=True,
            dense=True,
        )
        self._interval = ft.TextField(
            label=tr("settings.exchange_interval", lang),
            value=str(s.exchange_update_interval_minutes),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )
        self._reminder_time = ft.TextField(
            label=tr("settings.reminder_time", lang),
            value=s.reminder_time or "09:00",
            hint_text="09:00",
            expand=True,
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )
        self._reminder_days = ft.TextField(
            label=tr("settings.reminder_days", lang),
            value=str(getattr(s, "reminder_days", 3) or 3),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )
        self._notifications = ft.Switch(
            label=tr("settings.notifications", lang),
            value=s.notifications_enabled,
            on_change=lambda e: self._on_notifications_toggle(e),
        )
        self._debt_reminders = ft.Switch(
            label=tr("settings.debt_reminders", lang),
            value=s.debt_reminders,
        )
        self._sub_reminders = ft.Switch(
            label=tr("settings.subscription_reminders", lang),
            value=s.subscription_reminders,
        )
        self._check_balance_sub = ft.Switch(
            label=tr("settings.check_balance_before_subscription", lang),
            value=bool(getattr(s, "check_balance_before_subscription", True)),
        )
        self._goal_milestones = ft.Switch(
            label=tr("settings.goal_milestones", lang),
            value=s.goal_milestones,
        )
        self._biometric = ft.Switch(
            label=tr("settings.biometric", lang),
            value=s.biometric_enabled,
            on_change=lambda e: run_async(page, self._on_biometric_toggle, e),
        )
        self._biometric_hint = ft.Text(
            "",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._pin_tf = ft.TextField(
            label=tr("settings.pin", lang),
            password=True,
            can_reveal_password=True,
            expand=True,
            max_length=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )

        btn_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )

        scroll_body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                section(
                    tr("settings.appearance", lang),
                    ft.Icons.PALETTE_OUTLINED,
                    [
                        self._theme,
                        self._language,
                        self._currency,
                        ft.Text(
                            tr("settings.currency_hint", lang),
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    expanded=True,
                ),
                section(
                    tr("settings.rates", lang),
                    ft.Icons.CURRENCY_EXCHANGE,
                    [self._interval],
                ),
                section(
                    tr("settings.notifications", lang),
                    ft.Icons.NOTIFICATIONS_OUTLINED,
                    [
                        self._notifications,
                        self._debt_reminders,
                        self._sub_reminders,
                        self._check_balance_sub,
                        self._goal_milestones,
                        self._reminder_time,
                        self._reminder_days,
                    ],
                ),
                section(
                    tr("settings.security", lang),
                    ft.Icons.SECURITY,
                    [
                        self._biometric,
                        self._biometric_hint,
                        self._pin_tf,
                        ft.Row(
                            spacing=8,
                            wrap=True,
                            controls=[
                                ft.FilledTonalButton(
                                    tr("settings.set_pin", lang),
                                    icon=ft.Icons.LOCK_OUTLINE,
                                    style=btn_style,
                                    on_click=lambda _e: self.set_pin(),
                                ),
                                ft.TextButton(
                                    tr("settings.clear_pin", lang),
                                    icon=ft.Icons.LOCK_OPEN,
                                    on_click=lambda _e: run_async(
                                        page, self.clear_pin
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                section(
                    tr("settings.sections", lang),
                    ft.Icons.APPS_OUTLINED,
                    [
                        ft.Row(
                            wrap=True,
                            spacing=8,
                            run_spacing=8,
                            controls=[
                                ft.OutlinedButton(
                                    tr("nav.goals", lang),
                                    icon=ft.Icons.FLAG_OUTLINED,
                                    style=btn_style,
                                    on_click=lambda _e: state.open_secondary(
                                        "goals"
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("nav.debts", lang),
                                    icon=ft.Icons.CREDIT_SCORE,
                                    style=btn_style,
                                    on_click=lambda _e: state.open_secondary(
                                        "debts"
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("nav.subscriptions", lang),
                                    icon=ft.Icons.EVENT_REPEAT,
                                    style=btn_style,
                                    on_click=lambda _e: state.open_secondary(
                                        "subscriptions"
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("nav.currencies", lang),
                                    icon=ft.Icons.CURRENCY_EXCHANGE,
                                    style=btn_style,
                                    on_click=lambda _e: state.open_secondary(
                                        "currencies"
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                section(
                    tr("settings.export", lang),
                    ft.Icons.FILE_DOWNLOAD_OUTLINED,
                    [
                        ft.Row(
                            wrap=True,
                            spacing=8,
                            run_spacing=8,
                            controls=[
                                ft.OutlinedButton(
                                    tr("settings.export_json", lang),
                                    icon=ft.Icons.DATA_OBJECT,
                                    style=btn_style,
                                    on_click=lambda _e: run_async(
                                        page, self.export_json
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("settings.export_csv", lang),
                                    icon=ft.Icons.TABLE_VIEW,
                                    style=btn_style,
                                    on_click=lambda _e: run_async(
                                        page, self.export_csv
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("settings.export_pdf", lang),
                                    icon=ft.Icons.PICTURE_AS_PDF,
                                    style=btn_style,
                                    on_click=lambda _e: run_async(
                                        page, self.export_pdf
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                section(
                    tr("settings.backup_restore", lang),
                    ft.Icons.CLOUD_SYNC_OUTLINED,
                    [
                        ft.Row(
                            wrap=True,
                            spacing=8,
                            run_spacing=8,
                            controls=[
                                ft.OutlinedButton(
                                    tr("action.backup", lang),
                                    icon=ft.Icons.BACKUP,
                                    style=btn_style,
                                    on_click=lambda _e: run_async(
                                        page, self.backup
                                    ),
                                ),
                                ft.OutlinedButton(
                                    tr("action.restore", lang),
                                    icon=ft.Icons.SETTINGS_BACKUP_RESTORE,
                                    style=btn_style,
                                    on_click=lambda _e: run_async(
                                        page, self.restore_latest
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                section(
                    tr("settings.danger", lang),
                    ft.Icons.WARNING_AMBER_OUTLINED,
                    [
                        ft.Text(
                            tr("settings.delete_all_confirm", lang),
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.FilledButton(
                            tr("settings.delete_all_data", lang),
                            icon=ft.Icons.DELETE_FOREVER,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.ERROR,
                                color=ft.Colors.ON_ERROR,
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.Padding.symmetric(
                                    horizontal=16, vertical=12
                                ),
                            ),
                            on_click=lambda _e: self._confirm_wipe(),
                        ),
                    ],
                ),
                # Space so the last section is not hidden under the floating save bar.
                ft.Container(height=88),
            ],
        )

        floating_save = ft.Container(
            left=0,
            right=0,
            bottom=0,
            padding=ft.Padding.only(left=4, right=4, bottom=8),
            content=ft.Container(
                border_radius=18,
                bgcolor=ft.Colors.PRIMARY,
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                ink=True,
                on_click=lambda _e: run_async(page, self.save),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=20,
                    color="#00000044",
                    offset=ft.Offset(0, 6),
                ),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.SAVE_OUTLINED, color=ft.Colors.ON_PRIMARY),
                        ft.Text(
                            tr("action.save", lang),
                            color=ft.Colors.ON_PRIMARY,
                            weight=ft.FontWeight.W_700,
                            size=15,
                        ),
                    ],
                ),
            ),
        )

        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(tr("nav.settings", lang)),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                    content=ft.Stack(
                        expand=True,
                        controls=[
                            scroll_body,
                            floating_save,
                        ],
                    ),
                ),
            ],
        )
        self._sync_notification_controls()
        run_async(page, self._refresh_biometric_hint)

    def _notification_sub_controls(self) -> list[ft.Control]:
        return [
            self._debt_reminders,
            self._sub_reminders,
            self._check_balance_sub,
            self._goal_milestones,
            self._reminder_time,
            self._reminder_days,
        ]

    def _sync_notification_controls(self) -> None:
        """Disable sub-options when the master notifications switch is off."""
        enabled = bool(self._notifications.value)
        for ctrl in self._notification_sub_controls():
            ctrl.disabled = not enabled
            try:
                ctrl.update()
            except Exception:  # noqa: BLE001
                pass

    def _on_notifications_toggle(self, e: ft.ControlEvent) -> None:
        if bool(getattr(e.control, "value", False)):
            if not any(
                bool(getattr(ctrl, "value", False))
                for ctrl in (
                    self._debt_reminders,
                    self._sub_reminders,
                    self._goal_milestones,
                )
            ):
                self._debt_reminders.value = True
                self._sub_reminders.value = True
                self._goal_milestones.value = True
            run_async(self._page, request_push_permissions)
        self._sync_notification_controls()

    def _hint_for_status(self, status: BiometricStatus) -> str:
        lang = self._state.language
        if status is BiometricStatus.AVAILABLE:
            return tr("settings.biometric_hint_ok", lang)
        if status is BiometricStatus.DEVICE_NOT_PRESENT:
            return tr("settings.biometric_hint_missing", lang)
        if status is BiometricStatus.NOT_CONFIGURED:
            return tr("settings.biometric_hint_unconfigured", lang)
        if status is BiometricStatus.UNSUPPORTED:
            return tr("settings.biometric_unsupported", lang)
        if status is BiometricStatus.DISABLED_BY_POLICY:
            return tr("lock.biometric_policy", lang)
        if status is BiometricStatus.DEVICE_BUSY:
            return tr("lock.biometric_busy", lang)
        return tr("settings.biometric_unsupported", lang)

    async def _refresh_biometric_hint(self) -> None:
        crypto = self._state.container.encryption_service or EncryptionService()
        status = await crypto.refresh_biometric_status()
        self._biometric_hint.value = self._hint_for_status(status)
        try:
            self._biometric_hint.update()
        except Exception:  # noqa: BLE001
            pass

    async def _on_biometric_toggle(self, e: ft.ControlEvent) -> None:
        lang = self._state.language
        enabled = bool(getattr(e.control, "value", False))
        if not enabled:
            return
        repo = self._state.container.settings_repository
        has_pin = False
        if repo is not None and hasattr(repo, "get_pin_credentials"):
            pin_hash, pin_salt, _ = await repo.get_pin_credentials()
            has_pin = bool(pin_hash and pin_salt)
        if not has_pin:
            self._biometric.value = False
            try:
                self._biometric.update()
            except Exception:  # noqa: BLE001
                pass
            snack(self._page, tr("settings.biometric_need_pin", lang), error=True)
            return
        crypto = self._state.container.encryption_service or EncryptionService()
        status = await crypto.refresh_biometric_status()
        self._biometric_hint.value = self._hint_for_status(status)
        try:
            self._biometric_hint.update()
        except Exception:  # noqa: BLE001
            pass
        if status is not BiometricStatus.AVAILABLE:
            self._biometric.value = False
            try:
                self._biometric.update()
            except Exception:  # noqa: BLE001
                pass
            snack(self._page, self._hint_for_status(status), error=True)

    async def save(self) -> None:
        """Persist settings via use case and apply theme/language."""
        lang = self._state.language
        try:
            interval = int(self._interval.value or 60)
        except ValueError:
            interval = 60
        new_currency = normalize_currency_code(self._currency.value or "RUB")
        previous_currency = normalize_currency_code(
            self._state.settings.default_currency
        )
        previous_language = normalize_lang(self._state.settings.language)
        previous_theme = self._state.theme_mode
        try:
            reminder_days = int(self._reminder_days.value or 3)
        except ValueError:
            reminder_days = 3
        try:
            settings = AppSettings(
                id=self._state.settings.id,
                default_currency=new_currency,
                theme=self._theme.value or "system",
                language=normalize_lang(self._language.value or "ru"),
                exchange_update_interval_minutes=max(5, interval),
                notifications_enabled=bool(self._notifications.value),
                subscription_reminders=bool(self._sub_reminders.value),
                debt_reminders=bool(self._debt_reminders.value),
                goal_milestones=bool(self._goal_milestones.value),
                low_balance_threshold=self._state.settings.low_balance_threshold,
                reminder_time=(self._reminder_time.value or "09:00").strip(),
                reminder_days=max(0, min(365, reminder_days)),
                check_balance_before_subscription=bool(self._check_balance_sub.value),
                biometric_enabled=bool(self._biometric.value),
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return
        try:
            saved = await self._state.container.update_settings.execute(settings)
            repo = self._state.container.settings_repository
            if repo is not None and hasattr(repo, "set_pin_credentials"):
                pin_hash, pin_salt, _ = await repo.get_pin_credentials()
                if bool(self._biometric.value) and not (pin_hash and pin_salt):
                    snack(
                        self._page,
                        tr("settings.biometric_need_pin", lang),
                        error=True,
                    )
                    self._biometric.value = False
                    try:
                        self._biometric.update()
                    except Exception:  # noqa: BLE001
                        pass
                    saved = await self._state.container.update_settings.execute(
                        saved.model_copy(update={"biometric_enabled": False})
                    )
                elif pin_hash and pin_salt:
                    await repo.set_pin_credentials(
                        pin_hash,
                        pin_salt,
                        biometric_enabled=saved.biometric_enabled,
                    )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return

        # Keep the sole cash account in sync with the display currency.
        try:
            if new_currency != previous_currency:
                await self._migrate_account_currencies(previous_currency, new_currency)
            await align_sole_account_currency(self._state.container)
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
        if new_currency != previous_currency:
            uc = self._state.container.update_exchange_rates
            if uc is not None:
                try:
                    await uc.execute(base=new_currency)
                except Exception:  # noqa: BLE001
                    pass

        self._state.set_settings(saved)
        apply_theme(self._page, saved.theme)
        if saved.notifications_enabled:
            try:
                await request_push_permissions()
            except Exception:  # noqa: BLE001
                pass
        created = await schedule_reminders(
            self._state.container,
            saved,
            language=normalize_lang(saved.language),
        )
        if created:
            # OS push is emitted from NotificationService.push; refresh home banners.
            self._state.bump_refresh("dashboard")
        if previous_theme != saved.theme or previous_language != saved.language:
            self._state.request_view_rebuild()
        self._state.bump_refresh()
        self._page.update()
        snack(self._page, tr("action.saved", saved.language))

    async def _migrate_account_currencies(self, old: str, new: str) -> None:
        """Retarget accounts/txs still on the previous default currency.

        Typical case: user created a RUB cash account, then switched the app
        display currency to UZS — keep labels consistent without FX conversion
        of amounts (amounts stay as entered).
        """
        c = self._state.container
        if c.list_accounts is None or c.update_account is None:
            return
        accounts = await c.list_accounts.execute(active_only=False)
        for account in accounts:
            if normalize_currency_code(account.currency) != old:
                continue
            updated = account.model_copy(update={"currency": new})
            await c.update_account.execute(updated)
            if c.list_transactions is None or c.update_transaction is None:
                continue
            txs = await c.list_transactions.execute(account_id=account.id)
            for tx in txs:
                if normalize_currency_code(tx.currency) != old:
                    continue
                await c.update_transaction.execute(
                    tx.model_copy(update={"currency": new})
                )

    async def export_json(self) -> None:
        try:
            result = await self._state.container.export_data.execute(
                self._state.container.config.export_dir
            )
            snack(self._page, f"JSON: {result.path}")
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)

    async def export_csv(self) -> None:
        try:
            c = self._state.container
            txs = await c.list_transactions.execute()
            path = ExportService(c.config).export_transactions_csv(txs)
            snack(self._page, f"CSV: {path}")
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)

    async def export_pdf(self) -> None:
        try:
            c = self._state.container
            accounts = await c.list_accounts.execute()
            txs = await c.list_transactions.execute()
            goals = await c.list_goals.execute()
            debts = await c.list_debts.execute()
            subs = await c.list_subscriptions.execute()
            path = ExportService(c.config).export_summary_pdf(
                accounts=accounts,
                transactions=txs,
                goals=goals,
                debts=debts,
                subscriptions=subs,
                title="FinWise",
            )
            snack(self._page, f"PDF: {path}")
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)

    async def backup(self) -> None:
        try:
            path = BackupService(self._state.container.config).backup()
            snack(self._page, f"Backup: {path}")
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)

    async def restore_latest(self) -> None:
        lang = self._state.language
        service = BackupService(self._state.container.config)
        backups = service.list_backups()
        if not backups:
            snack(self._page, tr("settings.no_backups", lang), error=True)
            return
        latest = backups[0]
        confirm_dialog(
            self._page,
            title=tr("action.restore", lang),
            message=tr("settings.restore_confirm", lang),
            confirm_text=tr("action.restore", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=lambda: self._do_restore(latest),
        )

    async def _do_restore(self, backup_path) -> None:
        """Replace the live DB, rebind sessions, and reload settings."""
        import asyncio
        from pathlib import Path

        from lib.core.database import get_session_factory, reset_engine

        c = self._state.container
        path = Path(backup_path)
        try:
            # Release SQLite file locks before overwriting on Windows.
            await asyncio.to_thread(reset_engine)
            await asyncio.to_thread(
                lambda: BackupService(c.config).restore(
                    path, make_safety_copy=False
                )
            )
            factory = get_session_factory(c.config)
            c.rebind_session_factory(factory)
            if c.get_settings is not None:
                settings = await c.get_settings.execute()
                self._state.set_settings(settings, notify=False)
                apply_theme(self._page, settings.theme)
            self._state.request_view_rebuild()
            self._state.bump_refresh()
            self._page.update()
            snack(self._page, tr("settings.restore_done", self._state.language))
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)

    def set_pin(self) -> None:
        """Hash PIN and persist credentials via settings repository."""
        lang = self._state.language
        pin = (self._pin_tf.value or "").strip()
        if len(pin) < 4:
            snack(self._page, tr("settings.pin_min", lang), error=True)
            return
        creds = EncryptionService().hash_pin(pin)
        self._pin_tf.value = ""
        self._pin_tf.update()

        async def _persist() -> None:
            repo = self._state.container.settings_repository
            if repo is not None and hasattr(repo, "set_pin_credentials"):
                await repo.set_pin_credentials(
                    creds.pin_hash,
                    creds.pin_salt,
                    biometric_enabled=bool(self._biometric.value),
                )
            snack(self._page, tr("settings.pin_saved", lang))

        run_async(self._page, _persist)

    async def clear_pin(self) -> None:
        """Remove PIN lock credentials and disable biometric unlock."""
        lang = self._state.language
        repo = self._state.container.settings_repository
        if repo is not None and hasattr(repo, "clear_pin_credentials"):
            await repo.clear_pin_credentials()
        self._biometric.value = False
        try:
            self._biometric.update()
        except Exception:  # noqa: BLE001
            pass
        if self._state.settings.biometric_enabled:
            self._state.set_settings(
                self._state.settings.model_copy(
                    update={"biometric_enabled": False}
                ),
                notify=False,
            )
        snack(self._page, tr("settings.pin_cleared", lang))

    def _confirm_wipe(self) -> None:
        lang = self._state.language
        confirm_dialog(
            self._page,
            title=tr("settings.delete_all_data", lang),
            message=tr("settings.delete_all_confirm", lang),
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=self.wipe_all_data,
        )

    async def wipe_all_data(self) -> None:
        """Erase every table, then recreate defaults (settings / currencies / cash)."""
        import asyncio
        from pathlib import Path

        from lib.core.database import get_session_factory

        lang = self._state.language
        c = self._state.container
        try:
            await asyncio.to_thread(
                DataResetService(c.config).wipe_all,
                get_session_factory(c.config),
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return

        # Recreate defaults so the app stays usable.
        try:
            currencies_path = (
                Path(__file__).resolve().parents[3]
                / "assets"
                / "data"
                / "currencies.json"
            )
            if (
                c.currency_repository is not None
                and hasattr(c.currency_repository, "seed_from_json")
                and currencies_path.exists()
            ):
                await c.currency_repository.seed_from_json(currencies_path)
            if c.get_settings is not None:
                settings = await c.get_settings.execute()
                self._state.set_settings(settings, notify=False)
                apply_theme(self._page, settings.theme)
            if c.create_account is not None:
                from lib.domain.entities.account import Account

                await c.create_account.execute(
                    Account(
                        name=tr(
                            "account.default_cash",
                            self._state.language,
                        ),
                        currency=self._state.base_currency or c.config.default_currency,
                        initial_balance=0,
                        balance=0,
                        icon="wallet",
                        color="#2E7D32",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return

        self._state.request_view_rebuild()
        self._state.bump_refresh()
        self._page.update()
        snack(self._page, tr("settings.delete_all_done", lang))
