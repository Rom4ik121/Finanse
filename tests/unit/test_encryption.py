"""Encryption / PIN helpers."""

from __future__ import annotations

import pytest

from lib.infrastructure.services.encryption_service import EncryptionService


def test_pin_hash_roundtrip() -> None:
    service = EncryptionService()
    creds = service.hash_pin("1234")
    assert service.verify_pin("1234", creds.pin_hash, creds.pin_salt)
    assert not service.verify_pin("0000", creds.pin_hash, creds.pin_salt)


def test_pin_rejects_empty() -> None:
    service = EncryptionService()
    with pytest.raises(ValueError):
        service.hash_pin("")


def test_different_pins_different_hashes() -> None:
    service = EncryptionService()
    a = service.hash_pin("1111")
    b = service.hash_pin("2222")
    assert a.pin_hash != b.pin_hash
