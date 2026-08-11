"""Settings, export, align, and data wipe."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from lib.domain.entities.settings import AppSettings
from lib.domain.use_cases.align_currencies import align_sole_account_currency
from lib.infrastructure.services.data_reset_service import DataResetService
from lib.infrastructure.services.export_service import ExportService
from tests.conftest import run_async
from tests.factories import make_account, make_transaction


def test_settings_language_and_theme(container) -> None:
    async def _run() -> None:
        settings = await container.get_settings.execute()
        settings.language = "uz"
        settings.theme = "light"
        settings.default_currency = "UZS"
        saved = await container.update_settings.execute(settings)
        assert saved.language == "uz"
        assert saved.theme == "light"
        assert saved.default_currency == "UZS"

    run_async(_run())


def test_clear_pin_disables_biometric(container) -> None:
    async def _run() -> None:
        repo = container.settings_repository
        await repo.set_pin_credentials("hash", "salt", biometric_enabled=True)
        pin_hash, pin_salt, biometric = await repo.get_pin_credentials()
        assert pin_hash and pin_salt and biometric is True

        await repo.clear_pin_credentials()
        pin_hash, pin_salt, biometric = await repo.get_pin_credentials()
        assert pin_hash is None
        assert pin_salt is None
        assert biometric is False

        settings = await container.get_settings.execute()
        assert settings.biometric_enabled is False

    run_async(_run())


def test_container_rebind_session_factory_after_reset(container) -> None:
    from lib.core.database import get_session_factory, reset_engine

    old = container.settings_repository._session_factory
    reset_engine()
    factory = get_session_factory(container.config)
    container.rebind_session_factory(factory)
    assert container.settings_repository._session_factory is factory
    assert container.settings_repository._session_factory is not old

    async def _run() -> None:
        settings = await container.get_settings.execute()
        assert settings.id == "default"

    run_async(_run())


def test_export_data_use_case(container, tmp_path: Path) -> None:
    async def _run() -> None:
        await container.create_account.execute(make_account(name="Cash"))
        result = await container.export_data.execute(tmp_path / "exports")
        assert result.path.exists()
        payload = json.loads(result.path.read_text(encoding="utf-8"))
        assert result.counts["accounts"] >= 1
        assert "accounts" in payload

    run_async(_run())


def test_export_service_json_csv(tmp_path: Path) -> None:
    from lib.core.config import AppConfig

    cfg = AppConfig(data_dir=tmp_path)
    cfg.ensure_directories()
    svc = ExportService(cfg)
    json_path = svc.export_json({"accounts": [], "transactions": []})
    assert json_path.exists()
    csv_path = svc.export_transactions_csv([])
    assert csv_path.exists()


def test_align_sole_account_currency(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(
            make_account(currency="RUB", balance="100")
        )
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="10", currency="RUB")
        )
        settings = await container.get_settings.execute()
        settings.default_currency = "UZS"
        await container.update_settings.execute(settings)

        changed = await align_sole_account_currency(container)
        assert changed is True
        updated = await container.account_repository.get_by_id(acc.id)
        assert updated is not None
        assert updated.currency == "UZS"
        txs = await container.list_transactions.execute(account_id=acc.id)
        assert all(t.currency == "UZS" for t in txs)

        # Second call is a no-op.
        assert await align_sole_account_currency(container) is False

    run_async(_run())


def test_data_reset_wipes_accounts(container) -> None:
    from lib.core.database import get_session_factory

    async def _run() -> None:
        await container.create_account.execute(make_account())
        assert await container.list_accounts.execute()
        DataResetService(container.config).wipe_all(
            get_session_factory(container.config)
        )
        assert await container.list_accounts.execute() == []

    run_async(_run())
