"""Wipe all persisted application data."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import delete

from lib.core.config import AppConfig, get_default_config
from lib.core.database import Base
from lib.infrastructure.repositories._base import SessionFactory, session_scope

logger = logging.getLogger("finanse.infrastructure.services.data_reset")


class DataResetService:
    """Delete every row from all registered ORM tables."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or get_default_config()

    def wipe_all(self, session_factory: SessionFactory) -> None:
        """Remove all rows (accounts, txs, goals, debts, settings, etc.)."""
        # Ensure mappers are registered.
        import lib.infrastructure.db_models  # noqa: F401

        with session_scope(session_factory) as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(delete(table))
                logger.info("Cleared table %s", table.name)
        logger.info("All application data wiped")
