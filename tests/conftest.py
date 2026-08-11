"""Shared pytest fixtures for Finanse."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from pathlib import Path
from typing import Any, TypeVar

import pytest

from lib.core.config import AppConfig
from lib.core.database import init_db, reset_engine
from lib.core.dependencies import Container, build_container

T = TypeVar("T")


@pytest.fixture()
def container(tmp_path: Path) -> Container:
    """Isolated SQLite-backed DI container per test."""
    reset_engine()
    cfg = AppConfig(data_dir=tmp_path)
    cfg.ensure_directories()
    init_db(cfg)
    c = build_container(cfg, init_database=False)
    yield c
    reset_engine()


def run_async(coro: Coroutine[Any, Any, T] | Awaitable[T]) -> T:
    """Run an async coroutine in tests (no pytest-asyncio required)."""
    return asyncio.run(coro)  # type: ignore[arg-type]


@pytest.fixture()
def async_run() -> Callable[[Coroutine[Any, Any, T]], T]:
    """Fixture wrapper around :func:`run_async`."""
    return run_async
