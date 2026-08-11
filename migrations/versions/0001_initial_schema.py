"""Initial Finanse schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create baseline tables (idempotent with create_all for fresh installs)."""
    # Prefer application ``init_db`` / create_all for bootstrap.
    # This revision documents the baseline for Alembic tracking.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "accounts" in inspector.get_table_names():
        return
    from lib.core.database import Base
    import lib.infrastructure.db_models  # noqa: F401

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all application tables."""
    from lib.core.database import Base
    import lib.infrastructure.db_models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
