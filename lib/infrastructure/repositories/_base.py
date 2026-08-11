"""Shared helpers for SQLAlchemy repository implementations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, TypeVar

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("finanse.infrastructure.repositories")

SessionFactory = Callable[[], Session] | sessionmaker[Session]

T = TypeVar("T")


def ensure_utc(value: datetime | None) -> datetime | None:
    """Normalize datetimes to timezone-aware UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@contextmanager
def session_scope(session_factory: SessionFactory) -> Generator[Session, None, None]:
    """Provide a short-lived session with commit / rollback."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database session rolled back due to error")
        raise
    finally:
        session.close()
