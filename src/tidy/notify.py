"""Desktop notifications, gated by user settings and headless detection."""

from __future__ import annotations

import os
import shutil
import subprocess

from tidy import config

__all__ = ["notify"]

_LEVEL_URGENCY = {"info": "normal", "warn": "normal", "error": "critical"}


def _can_notify(cfg: dict) -> bool:
    if not cfg.get("notifications", True):
        return False
    # Headless (VPS): nothing to show a notification on.
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    return shutil.which("notify-send") is not None


def notify(title: str, message: str, level: str = "info") -> bool:
    """Show a desktop notification. Returns True if one was sent."""
    cfg = config.load()
    if not _can_notify(cfg):
        return False
    urgency = _LEVEL_URGENCY.get(level, "normal")
    subprocess.Popen(
        ["notify-send", "-u", urgency, "--app-name=tidy", title, message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True
