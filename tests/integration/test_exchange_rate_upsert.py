"""Exchange-rate upsert must not rewrite primary keys."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.currency import ExchangeRate
from tests.conftest import run_async


def test_upsert_rates_twice_keeps_stable_id(container) -> None:
    async def _run() -> None:
        first = await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="USD",
                    quote="UZS",
                    rate=Decimal("12000"),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )
        assert len(first) == 1
        first_id = first[0].id

        second = await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="USD",
                    quote="UZS",
                    rate=Decimal("12500"),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )
        assert len(second) == 1
        assert second[0].id == first_id
        assert second[0].rate == Decimal("12500")

        converted = await container.convert_currency.execute(
            Decimal("2"),
            from_currency="USD",
            to_currency="UZS",
        )
        assert converted == Decimal("25000.00")

    run_async(_run())
