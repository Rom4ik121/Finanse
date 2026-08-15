"""Shared color palette for accounts and categories.

Rows follow hue families (yellow → green → teal → blue → purple → pink →
red → orange → brown → gray), each with several tints from deep to pastel.
"""

from __future__ import annotations

from typing import Final


def _hsl_to_hex(hue: float, sat: float, light: float) -> str:
    """Convert HSL (hue 0–360, sat/light 0–1) to ``#RRGGBB``."""
    hue = hue % 360
    sat = min(1.0, max(0.0, sat))
    light = min(1.0, max(0.0, light))
    chroma = (1.0 - abs(2.0 * light - 1.0)) * sat
    hue_prime = hue / 60.0
    x = chroma * (1.0 - abs(hue_prime % 2.0 - 1.0))
    if 0.0 <= hue_prime < 1.0:
        r1, g1, b1 = chroma, x, 0.0
    elif 1.0 <= hue_prime < 2.0:
        r1, g1, b1 = x, chroma, 0.0
    elif 2.0 <= hue_prime < 3.0:
        r1, g1, b1 = 0.0, chroma, x
    elif 3.0 <= hue_prime < 4.0:
        r1, g1, b1 = 0.0, x, chroma
    elif 4.0 <= hue_prime < 5.0:
        r1, g1, b1 = x, 0.0, chroma
    else:
        r1, g1, b1 = chroma, 0.0, x
    match = light - chroma / 2.0
    r = int(round((r1 + match) * 255))
    g = int(round((g1 + match) * 255))
    b = int(round((b1 + match) * 255))
    return f"#{r:02X}{g:02X}{b:02X}"


# Lightness steps: deep → mid → pastel (6 columns, like the reference grids).
_TINTS: Final[tuple[float, ...]] = (0.28, 0.38, 0.48, 0.58, 0.70, 0.84)

# Hue families matching the 4-page reference (yellows, greens, teals, blues,
# violets, pinks, reds, oranges, browns, neutrals) plus extra in-between hues.
_HUES: Final[tuple[tuple[float, float], ...]] = (
    (48.0, 0.90),   # yellow
    (58.0, 0.82),   # gold
    (72.0, 0.72),   # lime
    (88.0, 0.68),   # yellow-green
    (110.0, 0.62),  # green
    (128.0, 0.58),  # grass
    (145.0, 0.55),  # forest
    (162.0, 0.58),  # teal
    (175.0, 0.62),  # aqua
    (188.0, 0.68),  # cyan
    (200.0, 0.70),  # sky
    (212.0, 0.72),  # azure
    (224.0, 0.68),  # blue
    (236.0, 0.62),  # royal
    (250.0, 0.58),  # indigo
    (262.0, 0.58),  # violet
    (275.0, 0.60),  # purple
    (288.0, 0.62),  # orchid
    (302.0, 0.62),  # magenta
    (318.0, 0.65),  # fuchsia
    (332.0, 0.68),  # pink
    (345.0, 0.70),  # rose
    (358.0, 0.72),  # crimson
    (10.0, 0.78),   # red
    (18.0, 0.82),   # vermilion
    (28.0, 0.86),   # orange
    (36.0, 0.88),   # amber
)

_NEUTRAL_HUES: Final[tuple[tuple[float, float], ...]] = (
    (28.0, 0.55),   # rust / brown
    (28.0, 0.32),   # taupe
    (20.0, 0.18),   # warm gray
    (0.0, 0.0),     # true gray
    (210.0, 0.12),  # blue-gray
    (220.0, 0.22),  # slate
)


def _row(hue: float, sat: float, tints: tuple[float, ...] = _TINTS) -> tuple[str, ...]:
    return tuple(_hsl_to_hex(hue, sat, tint) for tint in tints)


def _build_palette() -> tuple[str, ...]:
    colors: list[str] = ["#00897B"]  # brand teal first (legacy default)
    seen = {colors[0]}
    for hue, sat in _HUES + _NEUTRAL_HUES:
        for hex_color in _row(hue, sat):
            if hex_color not in seen:
                seen.add(hex_color)
                colors.append(hex_color)
    # Extra pale pastels and near-black accents.
    extras = (
        "#FFF8E1",
        "#F1F8E9",
        "#E0F2F1",
        "#E3F2FD",
        "#EDE7F6",
        "#FCE4EC",
        "#FFEBEE",
        "#FBE9E7",
        "#EFEBE9",
        "#FAFAFA",
        "#212121",
        "#263238",
        "#1A237E",
        "#004D40",
        "#B71C1C",
        "#E65100",
        "#F57F17",
        "#1B5E20",
        "#0D47A1",
        "#4A148C",
        "#880E4F",
        "#3E2723",
        "#FFFFFF",
        "#000000",
    )
    for hex_color in extras:
        if hex_color not in seen:
            seen.add(hex_color)
            colors.append(hex_color)
    return tuple(colors)


PALETTE_COLORS: Final[tuple[str, ...]] = _build_palette()
