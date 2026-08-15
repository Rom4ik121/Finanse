"""Category icon catalog keys resolve to Flet icons."""

from __future__ import annotations

from lib.core.config import CATEGORY_ICON_GROUPS, CATEGORY_ICONS
from lib.presentation.icon_registry import resolve_icon


def test_category_catalog_has_grouped_icons() -> None:
    group_keys = [key for key, _icons in CATEGORY_ICON_GROUPS]
    assert "icon_group.finance" in group_keys
    assert "icon_group.beauty" in group_keys
    assert "icon_group.bills" in group_keys
    assert "icon_group.sport" in group_keys
    assert "icon_group.leisure" in group_keys
    assert "icon_group.education" in group_keys
    assert "icon_group.farm" in group_keys
    assert len(CATEGORY_ICONS) >= 200


def test_every_category_icon_resolves() -> None:
    fallback = resolve_icon("category")
    unresolved: list[str] = []
    for key in CATEGORY_ICONS:
        if key == "category":
            continue
        if resolve_icon(key) is fallback:
            unresolved.append(key)
    assert unresolved == []
