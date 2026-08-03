"""GUI theme registry — CSS variable palettes for the 5 pixel themes."""

from __future__ import annotations

__all__ = ["THEMES", "theme_names", "validate_theme"]

THEMES: dict[str, dict[str, str]] = {
    "neon": {
        "bg": "#150a2e",
        "panel": "#1d1244",
        "panel2": "#2a1a5e",
        "border": "#21f3d9",
        "accent": "#ff4fd8",
        "accent2": "#21d0ff",
        "text": "#f6f2ff",
        "muted": "#b9aee6",
        "ok": "#21f371",
        "warn": "#ffc93c",
        "bad": "#ff5c7a",
    },
    "crt": {
        "bg": "#04070a",
        "panel": "#0a1216",
        "panel2": "#0f1e1e",
        "border": "#2bffb0",
        "accent": "#7dff8a",
        "accent2": "#e0ff5e",
        "text": "#c6ffd9",
        "muted": "#5fbf8f",
        "ok": "#3dff7a",
        "warn": "#ffd166",
        "bad": "#ff6b6b",
    },
    "gameboy": {
        "bg": "#aebcba",
        "panel": "#cfd8d5",
        "panel2": "#e3ebe8",
        "border": "#0f380f",
        "accent": "#9bbc0f",
        "accent2": "#5d7a1f",
        "text": "#1f3a12",
        "muted": "#57723f",
        "ok": "#0f380f",
        "warn": "#9bbc0f",
        "bad": "#7a1212",
    },
    "watermelon": {
        "bg": "#ff3d5a",
        "panel": "#ffe9f0",
        "panel2": "#fff4f8",
        "border": "#ff2d55",
        "accent": "#2b8c3e",
        "accent2": "#1e6d31",
        "text": "#3a1020",
        "muted": "#a04a62",
        "ok": "#2fb25a",
        "warn": "#ff9f1c",
        "bad": "#ff2d55",
    },
    "paper": {
        "bg": "#efe7d4",
        "panel": "#f6f1e3",
        "panel2": "#fffdf5",
        "border": "#5a4a36",
        "accent": "#c1440e",
        "accent2": "#47597e",
        "text": "#3a342a",
        "muted": "#8a7f6b",
        "ok": "#4a7b3a",
        "warn": "#c98a2b",
        "bad": "#c1440e",
    },
}


def theme_names() -> list[str]:
    return list(THEMES)


def validate_theme(name: str) -> bool:
    return name in THEMES
