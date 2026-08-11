"""Presentation layer: Flet UI, theme, state, and pages."""

__all__ = ["FinanseApp"]


def __getattr__(name: str):
    if name == "FinanseApp":
        from lib.presentation.app import FinanseApp

        return FinanseApp
    raise AttributeError(name)
