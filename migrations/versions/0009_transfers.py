"""Transfer pair columns on transactions.

Revision ID: 0009
Revises: 0008
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
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
    if not _has_table("transactions"):
        return
    if not _has_column("transactions", "transfer_id"):
        op.add_column(
            "transactions",
            sa.Column("transfer_id", sa.String(length=36), nullable=True),
        )
    if not _has_column("transactions", "transfer_peer_account_id"):
        op.add_column(
            "transactions",
            sa.Column("transfer_peer_account_id", sa.String(length=36), nullable=True),
        )
    if not _has_index("transactions", "ix_transactions_transfer_id"):
        op.create_index(
            "ix_transactions_transfer_id",
            "transactions",
            ["transfer_id"],
        )


def downgrade() -> None:
    if not _has_table("transactions"):
        return
    if _has_index("transactions", "ix_transactions_transfer_id"):
        op.drop_index("ix_transactions_transfer_id", table_name="transactions")
    if _has_column("transactions", "transfer_peer_account_id"):
        op.drop_column("transactions", "transfer_peer_account_id")
    if _has_column("transactions", "transfer_id"):
        op.drop_column("transactions", "transfer_id")
