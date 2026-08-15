"""Subscriptions: auto_charge flag.

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
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
    if not _has_column("subscriptions", "auto_charge"):
        op.add_column(
            "subscriptions",
            sa.Column(
                "auto_charge",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
    if not _has_index("subscriptions", "ix_subscriptions_next_billing"):
        op.create_index(
            "ix_subscriptions_next_billing",
            "subscriptions",
            ["status", "next_billing_date"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "subscriptions" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("subscriptions")}
        if "ix_subscriptions_next_billing" in existing:
            op.drop_index("ix_subscriptions_next_billing", table_name="subscriptions")
    if _has_column("subscriptions", "auto_charge"):
        op.drop_column("subscriptions", "auto_charge")
