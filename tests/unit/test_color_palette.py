"""Palette size and uniqueness."""

from __future__ import annotations

from lib.core.color_palette import PALETTE_COLORS
from lib.core.config import ACCOUNT_COLORS, CATEGORY_COLORS


def test_palette_is_large_and_unique() -> None:
    assert len(PALETTE_COLORS) >= 180
    assert len(set(PALETTE_COLORS)) == len(PALETTE_COLORS)
    assert PALETTE_COLORS[0] == "#00897B"


def test_account_and_category_share_palette() -> None:
    assert ACCOUNT_COLORS == PALETTE_COLORS
    assert CATEGORY_COLORS == PALETTE_COLORS
