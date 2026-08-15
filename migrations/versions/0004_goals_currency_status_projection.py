"""Goals: currency, status, projection cache, contribution credit.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if _has_column(table, column.name):
        return
    op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "goals",
        sa.Column("currency", sa.String(length=16), nullable=False, server_default="RUB"),
    )
    _add_column_if_missing(
        "goals",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )
    _add_column_if_missing(
        "goals",
        sa.Column("cached_projection", sa.JSON(), nullable=True),
    )
    _add_column_if_missing(
        "transactions",
        sa.Column("goal_credit_amount", sa.Numeric(18, 2), nullable=True),
    )

    # Backfill status from is_completed for existing rows.
    op.execute(
        sa.text(
            "UPDATE goals SET status = 'completed' "
            "WHERE is_completed = 1 AND (status IS NULL OR status = 'active')"
        )
    )

    # Indexes (idempotent where supported).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes("goals")} if "goals" in inspector.get_table_names() else set()
    if "ix_goals_status" not in existing:
        op.create_index("ix_goals_status", "goals", ["status"])
    if "ix_goals_deadline" not in existing:
        op.create_index("ix_goals_deadline", "goals", ["deadline"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "goals" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("goals")}
        if "ix_goals_deadline" in existing:
            op.drop_index("ix_goals_deadline", table_name="goals")
        if "ix_goals_status" in existing:
            op.drop_index("ix_goals_status", table_name="goals")
        for col in ("cached_projection", "status", "currency"):
            if _has_column("goals", col):
                op.drop_column("goals", col)
    if _has_column("transactions", "goal_credit_amount"):
        op.drop_column("transactions", "goal_credit_amount")
