"""Terminal-safe theme accents for the TUI.

Maps the 5 GUI themes onto terminal-friendly accent colors.
"""

from __future__ import annotations

__all__ = ["ACCENTS", "ORDER", "accent_for", "cycle_theme"]

ACCENTS: dict[str, str] = {
    "neon": "#21f3d9",
    "crt": "#3dff7a",
    "gameboy": "#9bbc0f",
    "watermelon": "#ff2d55",
    "paper": "#c1440e",
}

ORDER: tuple[str, ...] = ("neon", "crt", "gameboy", "watermelon", "paper")


def accent_for(theme: str) -> str:
    """Return the accent color for a theme (defaults to neon)."""
    return ACCENTS.get(theme, ACCENTS["neon"])


def cycle_theme(current: str) -> str:
    """Return the next theme in the cycle."""
    try:
        index = ORDER.index(current)
        return ORDER[(index + 1) % len(ORDER)]
    except ValueError:
        return ORDER[0]
