"""Safe convert helper and presentation tr coverage."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from lib.domain.entities.currency import ExchangeRate
from lib.presentation.utils import safe_convert, tr
from tests.conftest import run_async


def test_tr_all_nav_keys() -> None:
    for key in (
        "nav.home",
        "nav.accounts",
        "nav.transactions",
        "nav.goals",
        "nav.debts",
        "nav.subscriptions",
        "nav.settings",
        "nav.currencies",
    ):
        for lang in ("ru", "en", "uz"):
            assert tr(key, lang)


def test_safe_convert_same_and_missing(container) -> None:
    async def _run() -> None:
        same = await safe_convert(container, Decimal("10"), "RUB", "rub")
        assert same == Decimal("10.00")

        missing = await safe_convert(container, Decimal("1"), "XXX", "YYY")
        assert missing is None

        await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="USD",
                    quote="RUB",
                    rate=Decimal("100"),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )
        converted = await safe_convert(container, Decimal("2"), "USD", "RUB")
        assert converted == Decimal("200.00")

        none_uc = await safe_convert(
            SimpleNamespace(convert_currency=None),
            Decimal("1"),
            "USD",
            "RUB",
        )
        assert none_uc is None

    run_async(_run())
