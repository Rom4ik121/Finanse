"""Logging configuration for the Finanse application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    *,
    level: int | str = logging.INFO,
    log_dir: Optional[Path] = None,
    log_filename: str = "finanse.log",
    console: bool = True,
) -> logging.Logger:
    """Configure root application logging.

    Args:
        level: Logging level name or numeric level.
        log_dir: Optional directory for the rotating/file handler.
        log_filename: Log file name inside ``log_dir``.
        console: Whether to also emit logs to stderr.

    Returns:
        The configured ``finanse`` logger.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("finanse")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / log_filename,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Quiet noisy third-party loggers by default.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.debug("Logging initialized (level=%s)", level)
    return logger
