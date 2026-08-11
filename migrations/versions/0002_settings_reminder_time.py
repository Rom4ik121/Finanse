"""Add settings.reminder_time column.

Revision ID: 0002_reminder_time
Revises: 0001_initial
Create Date: 2026-08-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reminder_time"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("settings")}
    if "reminder_time" in columns:
        return
    with op.batch_alter_table("settings") as batch:
        batch.add_column(
            sa.Column(
                "reminder_time",
                sa.String(length=8),
                nullable=False,
                server_default="09:00",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("settings")}
    if "reminder_time" not in columns:
        return
    with op.batch_alter_table("settings") as batch:
        batch.drop_column("reminder_time")
