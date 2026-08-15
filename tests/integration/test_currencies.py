"""FX rates and currency conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from lib.domain.entities.currency import ExchangeRate
from tests.conftest import run_async


def test_upsert_rates_and_convert_direct(container) -> None:
    async def _run() -> None:
        await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="USD",
                    quote="UZS",
                    rate=Decimal("12500"),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )
        converted = await container.convert_currency.execute(
            Decimal("2"),
            from_currency="USD",
            to_currency="UZS",
        )
        assert converted == Decimal("25000.00")

    run_async(_run())


def test_convert_inverse_rate(container) -> None:
    async def _run() -> None:
        await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="USD",
                    quote="RUB",
                    rate=Decimal("90"),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )
        # Inverse of USD/RUB=90 → RUB→USD
        converted = await container.convert_currency.execute(
            Decimal("180"),
            from_currency="RUB",
            to_currency="USD",
        )
        assert converted == Decimal("2.00")

    run_async(_run())


def test_convert_cross_via_app_base(container) -> None:
    """BTC/USD is not stored; convert through UZS→BTC and UZS→USD."""

    async def _run() -> None:
        await container.update_exchange_rates.execute(
            rates=[
                ExchangeRate(
                    base="UZS",
                    quote="USD",
                    rate=Decimal("0.00008"),
                    updated_at=datetime.now(timezone.utc),
                ),
                ExchangeRate(
                    base="UZS",
                    quote="BTC",
                    rate=Decimal("0.0000000008"),
                    updated_at=datetime.now(timezone.utc),
                ),
            ]
        )
        converted = await container.convert_currency.execute(
            Decimal("1"),
            from_currency="BTC",
            to_currency="USD",
        )
        assert converted == Decimal("100000.00")

        unit = await container.convert_currency.execute(
            Decimal("1"),
            from_currency="UZS",
            to_currency="USD",
            quantize=False,
        )
        assert unit == Decimal("0.00008")

    run_async(_run())


def test_convert_same_currency(container) -> None:
    async def _run() -> None:
        result = await container.convert_currency.execute(
            Decimal("10.5"),
            from_currency="RUB",
            to_currency="rub",
        )
        assert result == Decimal("10.50")

    run_async(_run())


def test_convert_missing_rate(container) -> None:
    async def _run() -> None:
        with pytest.raises(ValueError):
            await container.convert_currency.execute(
                Decimal("1"),
                from_currency="AAA",
                to_currency="BBB",
            )

    run_async(_run())
