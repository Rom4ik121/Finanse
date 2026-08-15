"""Subscriptions: flexible periodicity, status, settings; subscription_id on txs.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def _has_index(table: str, name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(ix["name"] == name for ix in inspector.get_indexes(table))


def upgrade() -> None:
    if not _has_column("transactions", "subscription_id"):
        op.add_column(
            "transactions",
            sa.Column("subscription_id", sa.String(36), nullable=True),
        )

    sub_columns = [
        ("custom_interval_days", sa.Column("custom_interval_days", sa.Integer(), nullable=True)),
        ("start_date", sa.Column("start_date", sa.Date(), nullable=True)),
        ("end_date", sa.Column("end_date", sa.Date(), nullable=True)),
        ("max_payments", sa.Column("max_payments", sa.Integer(), nullable=True)),
        ("payments_made", sa.Column("payments_made", sa.Integer(), nullable=False, server_default="0")),
        ("status", sa.Column("status", sa.String(16), nullable=False, server_default="active")),
        ("last_skip_date", sa.Column("last_skip_date", sa.Date(), nullable=True)),
    ]
    for name, column in sub_columns:
        if not _has_column("subscriptions", name):
            op.add_column("subscriptions", column)

    bind = op.get_bind()
    # Backfill start_date / status from existing rows.
    if _has_column("subscriptions", "start_date"):
        bind.exec_driver_sql(
            "UPDATE subscriptions SET start_date = date(next_billing_date) "
            "WHERE start_date IS NULL"
        )
    if _has_column("subscriptions", "status"):
        bind.exec_driver_sql(
            "UPDATE subscriptions SET status = CASE "
            "WHEN is_active = 1 THEN 'active' ELSE 'paused' END "
            "WHERE status IS NULL OR status = ''"
        )

    if not _has_column("settings", "reminder_days"):
        op.add_column(
            "settings",
            sa.Column("reminder_days", sa.Integer(), nullable=False, server_default="3"),
        )
    if not _has_column("settings", "check_balance_before_subscription"):
        op.add_column(
            "settings",
            sa.Column(
                "check_balance_before_subscription",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )

    if _has_column("transactions", "subscription_id") and not _has_index(
        "transactions", "ix_transactions_subscription_id"
    ):
        op.create_index(
            "ix_transactions_subscription_id",
            "transactions",
            ["subscription_id"],
        )
    if _has_column("subscriptions", "status") and not _has_index(
        "subscriptions", "ix_subscriptions_status"
    ):
        op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    if _has_column("subscriptions", "start_date") and not _has_index(
        "subscriptions", "ix_subscriptions_start_date"
    ):
        op.create_index("ix_subscriptions_start_date", "subscriptions", ["start_date"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscriptions" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("subscriptions")}
        if "ix_subscriptions_start_date" in existing:
            op.drop_index("ix_subscriptions_start_date", table_name="subscriptions")
        if "ix_subscriptions_status" in existing:
            op.drop_index("ix_subscriptions_status", table_name="subscriptions")

    if "transactions" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("transactions")}
        if "ix_transactions_subscription_id" in existing:
            op.drop_index("ix_transactions_subscription_id", table_name="transactions")

    for table, column in (
        ("settings", "check_balance_before_subscription"),
        ("settings", "reminder_days"),
        ("subscriptions", "last_skip_date"),
        ("subscriptions", "status"),
        ("subscriptions", "payments_made"),
        ("subscriptions", "max_payments"),
        ("subscriptions", "end_date"),
        ("subscriptions", "start_date"),
        ("subscriptions", "custom_interval_days"),
        ("transactions", "subscription_id"),
    ):
        if _has_column(table, column):
            op.drop_column(table, column)
