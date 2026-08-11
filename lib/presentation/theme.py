"""Finanse visual system — dark-first, high-contrast light alternative.

Palette direction: deep slate + mint/teal accents (no purple glow).
"""

from __future__ import annotations

import flet as ft

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

# Dark
DARK_BG = "#0B1220"
DARK_SURFACE = "#121A2B"
DARK_SURFACE_2 = "#1A2438"
DARK_SURFACE_3 = "#243049"
DARK_BORDER = "#2C3A55"
DARK_TEXT = "#F1F5F9"
DARK_MUTED = "#94A3B8"
DARK_PRIMARY = "#2DD4BF"
DARK_PRIMARY_DIM = "#14B8A6"
DARK_ON_PRIMARY = "#042F2E"
DARK_INCOME = "#4ADE80"
DARK_EXPENSE = "#F87171"
DARK_WARN = "#FBBF24"

# Light — high contrast, crisp details
LIGHT_BG = "#F1F5F9"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_SURFACE_2 = "#F8FAFC"
LIGHT_SURFACE_3 = "#E2E8F0"
LIGHT_BORDER = "#CBD5E1"
LIGHT_TEXT = "#0F172A"
LIGHT_MUTED = "#475569"
LIGHT_PRIMARY = "#0F766E"
LIGHT_PRIMARY_DIM = "#0D9488"
LIGHT_ON_PRIMARY = "#FFFFFF"
LIGHT_INCOME = "#15803D"
LIGHT_EXPENSE = "#B91C1C"
LIGHT_WARN = "#B45309"

SEED_COLOR = DARK_PRIMARY
FONT_FAMILY = "Segoe UI"
FONT_FAMILY_DISPLAY = "Segoe UI Semibold"


def light_color_scheme() -> ft.ColorScheme:
    """High-contrast light scheme — all UI details stay readable."""
    return ft.ColorScheme(
        primary=LIGHT_PRIMARY,
        on_primary=LIGHT_ON_PRIMARY,
        primary_container="#CCFBF1",
        on_primary_container="#042F2E",
        secondary=LIGHT_PRIMARY_DIM,
        on_secondary=LIGHT_ON_PRIMARY,
        secondary_container="#D1FAE5",
        on_secondary_container="#064E3B",
        tertiary="#0369A1",
        on_tertiary="#FFFFFF",
        tertiary_container="#E0F2FE",
        on_tertiary_container="#0C4A6E",
        surface=LIGHT_BG,
        on_surface=LIGHT_TEXT,
        surface_container_lowest=LIGHT_SURFACE,
        surface_container_low=LIGHT_SURFACE_2,
        surface_container=LIGHT_SURFACE,
        surface_container_high=LIGHT_SURFACE_2,
        surface_container_highest=LIGHT_SURFACE_3,
        on_surface_variant=LIGHT_MUTED,
        outline=LIGHT_BORDER,
        outline_variant="#E2E8F0",
        error="#DC2626",
        on_error="#FFFFFF",
        error_container="#FEE2E2",
        on_error_container="#7F1D1D",
        inverse_surface=DARK_SURFACE,
        on_inverse_surface=DARK_TEXT,
        inverse_primary=DARK_PRIMARY,
        shadow="#0F172A33",
        scrim="#0F172A66",
    )


def dark_color_scheme() -> ft.ColorScheme:
    """Modern dark slate + mint accent scheme."""
    return ft.ColorScheme(
        primary=DARK_PRIMARY,
        on_primary=DARK_ON_PRIMARY,
        primary_container="#115E59",
        on_primary_container="#CCFBF1",
        secondary="#5EEAD4",
        on_secondary="#042F2E",
        secondary_container="#134E4A",
        on_secondary_container="#CCFBF1",
        tertiary="#38BDF8",
        on_tertiary="#0C4A6E",
        tertiary_container="#075985",
        on_tertiary_container="#E0F2FE",
        surface=DARK_BG,
        on_surface=DARK_TEXT,
        surface_container_lowest="#070B14",
        surface_container_low=DARK_SURFACE,
        surface_container=DARK_SURFACE,
        surface_container_high=DARK_SURFACE_2,
        surface_container_highest=DARK_SURFACE_3,
        on_surface_variant=DARK_MUTED,
        outline=DARK_BORDER,
        outline_variant="#1F2A40",
        error=DARK_EXPENSE,
        on_error="#450A0A",
        error_container="#7F1D1D",
        on_error_container="#FECACA",
        inverse_surface=LIGHT_SURFACE,
        on_inverse_surface=LIGHT_TEXT,
        inverse_primary=LIGHT_PRIMARY,
        shadow="#00000066",
        scrim="#00000099",
    )


def build_theme(*, dark: bool = False) -> ft.Theme:
    """Build a polished Material theme for light or dark appearance."""
    return ft.Theme(
        color_scheme_seed=SEED_COLOR,
        color_scheme=dark_color_scheme() if dark else light_color_scheme(),
        font_family=FONT_FAMILY,
    )


def resolve_theme_mode(mode: str | ft.ThemeMode | None) -> ft.ThemeMode:
    """Map a settings string / ThemeMode to :class:`ft.ThemeMode`."""
    if isinstance(mode, ft.ThemeMode):
        return mode
    value = str(mode or "dark").lower()
    # Handle enum string forms like "ThemeMode.DARK" / "dark"
    if "." in value:
        value = value.split(".")[-1]
    if value == "light":
        return ft.ThemeMode.LIGHT
    if value == "system":
        return ft.ThemeMode.SYSTEM
    return ft.ThemeMode.DARK


def is_dark_mode(page: ft.Page, mode: str | ft.ThemeMode | None = None) -> bool:
    """Best-effort dark-mode detection for conditional styling."""
    source = mode if mode is not None else getattr(page, "theme_mode", None)
    resolved = resolve_theme_mode(source)
    if resolved == ft.ThemeMode.DARK:
        return True
    if resolved == ft.ThemeMode.LIGHT:
        return False
    # SYSTEM — prefer dark as product default when platform is unknown.
    platform_brightness = getattr(page, "platform_brightness", None)
    if platform_brightness is not None and str(platform_brightness).lower().endswith(
        "light"
    ):
        return False
    return True


def apply_theme(page: ft.Page, mode: str | None = "dark") -> None:
    """Apply light/dark themes and theme mode to the page."""
    page.theme = build_theme(dark=False)
    page.dark_theme = build_theme(dark=True)
    page.theme_mode = resolve_theme_mode(mode)
    page.bgcolor = ft.Colors.SURFACE
    page.fonts = {
        "Segoe UI": "Segoe UI",
        "Segoe UI Semibold": "Segoe UI Semibold",
    }
    # Floating nav lives in FinanseApp shell (rounded host), not page.navigation_bar.


def page_gradient(dark: bool) -> ft.LinearGradient:
    """Subtle atmospheric background gradient for shells / lock screen."""
    if dark:
        return ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[DARK_BG, "#0E1A2E", "#0B1F24"],
        )
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=[LIGHT_BG, "#E8F5F3", LIGHT_BG],
    )
