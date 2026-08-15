"""Budgets table and settings.budget_alerts.

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


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
    if _has_table("settings") and not _has_column("settings", "budget_alerts"):
        op.add_column(
            "settings",
            sa.Column(
                "budget_alerts",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
    if not _has_table("budgets"):
        op.create_table(
            "budgets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("category_id", sa.String(length=128), nullable=False),
            sa.Column("month", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("amount_limit", sa.Numeric(18, 2), nullable=False),
            sa.Column(
                "spent",
                sa.Numeric(18, 2),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "last_alert_level",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["category_id"],
                ["categories.name"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            ),
            sa.UniqueConstraint(
                "category_id",
                "month",
                "year",
                name="uq_budgets_category_month",
            ),
        )
    if _has_table("budgets") and not _has_index("budgets", "ix_budgets_month_year"):
        op.create_index("ix_budgets_month_year", "budgets", ["month", "year"])
    if _has_table("budgets") and not _has_index("budgets", "ix_budgets_category_month"):
        op.create_index(
            "ix_budgets_category_month",
            "budgets",
            ["category_id", "month", "year"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "budgets" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("budgets")}
        if "ix_budgets_category_month" in existing:
            op.drop_index("ix_budgets_category_month", table_name="budgets")
        if "ix_budgets_month_year" in existing:
            op.drop_index("ix_budgets_month_year", table_name="budgets")
        op.drop_table("budgets")
    if _has_column("settings", "budget_alerts"):
        op.drop_column("settings", "budget_alerts")
