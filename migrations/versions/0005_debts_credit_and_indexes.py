"""Debts: debt_credit_amount on transactions; due_date index.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("transactions", "debt_credit_amount"):
        op.add_column(
            "transactions",
            sa.Column("debt_credit_amount", sa.Numeric(18, 2), nullable=True),
        )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "debts" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("debts")}
        if "ix_debts_status" not in existing:
            op.create_index("ix_debts_status", "debts", ["status"])
        if "ix_debts_due_date" not in existing:
            op.create_index("ix_debts_due_date", "debts", ["due_date"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "debts" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("debts")}
        if "ix_debts_due_date" in existing:
            op.drop_index("ix_debts_due_date", table_name="debts")
        if "ix_debts_status" in existing:
            op.drop_index("ix_debts_status", table_name="debts")
    if _has_column("transactions", "debt_credit_amount"):
        op.drop_column("transactions", "debt_credit_amount")
