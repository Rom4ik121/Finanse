"""UI smoke: presentation widgets build without a live Flet page session."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone

import flet as ft

from lib.domain.entities.account import Account
from lib.domain.entities.debt import Debt, DebtDirection
from lib.domain.entities.subscription import Periodicity, Subscription
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.presentation.currency_options import currency_dropdown_options
from lib.presentation.widgets.account_card import AccountCard
from lib.presentation.widgets.charts import build_line_chart_image, build_pie_chart_image
from lib.presentation.widgets.debt_card import DebtCard
from lib.presentation.widgets.subscription_card import SubscriptionCard
from lib.presentation.widgets.transaction_tile import TransactionTile


def test_currency_dropdown_options_localized() -> None:
    options = currency_dropdown_options(lang="uz", include_crypto=False)
    assert options
    assert options[0].key
    assert "—" in (options[0].text or "")


def test_account_card_builds() -> None:
    acc = Account(
        name="Cash",
        currency="RUB",
        initial_balance=Decimal("10"),
        balance=Decimal("10"),
        icon="wallet",
        color="#2E7D32",
    )
    card = AccountCard(acc, language="en")
    assert card is not None


def test_transaction_tile_builds() -> None:
    tx = Transaction(
        account_id="a1",
        amount=Decimal("12.5"),
        category="Food",
        date=datetime.now(timezone.utc),
        type=TransactionType.EXPENSE,
        currency="USD",
    )
    tile = TransactionTile(tx, language="ru")
    assert tile is not None


def test_subscription_and_debt_cards_build() -> None:
    sub = Subscription(
        name="Netflix",
        amount=Decimal("10"),
        account_id="a1",
        next_billing_date=datetime.now(timezone.utc),
        periodicity=Periodicity.MONTHLY,
    )
    assert SubscriptionCard(sub, language="uz") is not None

    debt = Debt(
        counterparty="Bank",
        amount=Decimal("100"),
        remaining_amount=Decimal("100"),
        direction=DebtDirection.I_OWE,
    )
    assert DebtCard(debt, language="en") is not None


def test_charts_empty_and_with_data() -> None:
    empty_pie = build_pie_chart_image([], [], language="en")
    assert isinstance(empty_pie, (ft.Image, ft.Container))

    pie = build_pie_chart_image(["Food"], [Decimal("10")], language="ru")
    assert isinstance(pie, (ft.Image, ft.Container))

    empty_line = build_line_chart_image([], [], [], language="uz")
    assert isinstance(empty_line, (ft.Image, ft.Container))

    line = build_line_chart_image(
        ["01-01", "01-02"],
        [Decimal("10"), Decimal("20")],
        [Decimal("5"), Decimal("8")],
        language="en",
    )
    assert isinstance(line, (ft.Image, ft.Container))


def test_charts_native_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "lib.presentation.widgets.charts._prefer_native_charts",
        lambda: True,
    )
    pie = build_pie_chart_image(["Food", "Travel"], [Decimal("80"), Decimal("20")], language="ru")
    assert isinstance(pie, ft.Container)
    line = build_line_chart_image(
        ["01-01"],
        [Decimal("10")],
        [Decimal("5")],
        language="ru",
    )
    assert isinstance(line, ft.Container)


def test_budgets_page_importable() -> None:
    from lib.presentation.pages.budgets import BudgetsPage

    assert BudgetsPage is not None
