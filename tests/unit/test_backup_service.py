"""BackupService filesystem roundtrip."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.core.config import AppConfig
from lib.infrastructure.services.backup_service import BackupService, BackupServiceError


def test_backup_restore_roundtrip(tmp_path: Path) -> None:
    cfg = AppConfig(data_dir=tmp_path)
    cfg.ensure_directories()
    cfg.db_path.write_text("sqlite-payload", encoding="utf-8")

    svc = BackupService(cfg)
    backup = svc.backup(label="test")
    assert backup.exists()
    assert backup.name.endswith("_test.db")

    cfg.db_path.write_text("changed", encoding="utf-8")
    restored = svc.restore(backup, make_safety_copy=True)
    assert restored.read_text(encoding="utf-8") == "sqlite-payload"
    assert svc.list_backups()


def test_backup_missing_db(tmp_path: Path) -> None:
    cfg = AppConfig(data_dir=tmp_path)
    cfg.ensure_directories()
    svc = BackupService(cfg)
    with pytest.raises(BackupServiceError):
        svc.backup()
