"""Localization dictionary and helpers."""

from __future__ import annotations

from lib.infrastructure.services.localization import (
    STRINGS,
    SUPPORTED_LANGS,
    available_keys,
    localize_category_name,
    merge_strings,
    normalize_lang,
    t,
)


def test_supported_langs() -> None:
    assert SUPPORTED_LANGS == ("ru", "en", "uz")


def test_normalize_lang() -> None:
    assert normalize_lang("ru-RU") == "ru"
    assert normalize_lang("en_US") == "en"
    assert normalize_lang("uz-Latn") == "uz"
    assert normalize_lang(None) == "ru"
    assert normalize_lang("xx") == "ru"


def test_every_key_has_all_langs() -> None:
    for key, entry in STRINGS.items():
        for lang in SUPPORTED_LANGS:
            assert lang in entry, f"{key} missing {lang}"
            assert entry[lang].strip(), f"{key}/{lang} empty"


def test_t_returns_correct_language() -> None:
    assert t("nav.home", "ru") == "Главная"
    assert t("nav.home", "en") == "Home"
    assert t("nav.home", "uz") == "Bosh sahifa"


def test_t_missing_key_and_default() -> None:
    assert t("does.not.exist") == "does.not.exist"
    assert t("does.not.exist", default="fallback") == "fallback"


def test_localize_category_name() -> None:
    assert localize_category_name("Еда", "ru") == "Еда"
    assert localize_category_name("Еда", "en") == "Food"
    assert localize_category_name("Еда", "uz") == "Ovqat"
    assert localize_category_name("Custom", "en") == "Custom"


def test_merge_strings_and_available_keys() -> None:
    merge_strings({"test.tmp.key": {"ru": "А", "en": "A", "uz": "A"}})
    assert t("test.tmp.key", "ru") == "А"
    assert "test.tmp.key" in available_keys()
