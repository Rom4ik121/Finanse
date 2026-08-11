"""SQLite database backup and restore."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lib.core.config import AppConfig, get_default_config

logger = logging.getLogger("finanse.infrastructure.services.backup")


class BackupServiceError(Exception):
    """Raised when backup or restore fails."""


class BackupService:
    """Copy the SQLite DB file to / from the configured backup directory."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or get_default_config()
        self._config.ensure_directories()

    @property
    def db_path(self) -> Path:
        return self._config.db_path

    @property
    def backup_dir(self) -> Path:
        return self._config.backup_dir

    def backup(self, *, label: Optional[str] = None) -> Path:
        """Create a timestamped copy of the database.

        Args:
            label: Optional suffix added to the filename.

        Returns:
            Path to the created backup file.

        Raises:
            BackupServiceError: If the source DB is missing or copy fails.
        """
        source = self.db_path
        if not source.exists():
            logger.error("Cannot backup; database not found at %s", source)
            raise BackupServiceError(f"Database not found: {source}")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        target = self.backup_dir / f"finanse_{stamp}{suffix}.db"

        try:
            # Also copy WAL/SHM sidecars when present for a consistent snapshot.
            self._copy_sqlite_bundle(source, target)
            logger.info("Database backed up to %s", target)
            return target
        except OSError as exc:
            logger.exception("Backup failed")
            raise BackupServiceError(f"Backup failed: {exc}") from exc

    def restore(self, backup_path: Path | str, *, make_safety_copy: bool = True) -> Path:
        """Restore the database from a backup file.

        Args:
            backup_path: Path to a ``.db`` backup.
            make_safety_copy: When True, backup the current DB first.

        Returns:
            Path to the restored database file.
        """
        source = Path(backup_path)
        if not source.exists():
            raise BackupServiceError(f"Backup file not found: {source}")

        target = self.db_path
        try:
            if make_safety_copy and target.exists():
                safety = self.backup(label="pre_restore")
                logger.info("Safety backup created at %s", safety)

            self._remove_sqlite_sidecars(target)
            self._copy_sqlite_bundle(source, target)
            logger.info("Database restored from %s to %s", source, target)
            return target
        except OSError as exc:
            logger.exception("Restore failed")
            raise BackupServiceError(f"Restore failed: {exc}") from exc

    def list_backups(self) -> list[Path]:
        """Return backup files newest first."""
        return sorted(
            self.backup_dir.glob("finanse_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def delete_backup(self, backup_path: Path | str) -> None:
        """Delete a backup file and any sidecars."""
        path = Path(backup_path)
        try:
            self._remove_sqlite_sidecars(path)
            if path.exists():
                path.unlink()
            logger.info("Deleted backup %s", path)
        except OSError as exc:
            logger.exception("Failed to delete backup %s", path)
            raise BackupServiceError(f"Delete failed: {exc}") from exc

    @staticmethod
    def _copy_sqlite_bundle(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        # SQLite uses ``file.db-wal`` / ``file.db-shm``.
        for sidecar_suffix in ("-wal", "-shm"):
            src_side = Path(str(source) + sidecar_suffix)
            if src_side.exists():
                shutil.copy2(src_side, Path(str(target) + sidecar_suffix))

    @staticmethod
    def _remove_sqlite_sidecars(db_path: Path) -> None:
        for sidecar_suffix in ("-wal", "-shm"):
            side = Path(str(db_path) + sidecar_suffix)
            if side.exists():
                side.unlink()
