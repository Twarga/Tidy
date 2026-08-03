"""System tray icon + right-click mini-panel.

Right-clicking the tray icon shows quick controls: status, per-repo push,
backup/pull all, theme switcher, show window, quit.

Degrades gracefully when no display is available (headless VPS).
"""

from __future__ import annotations

import os
import threading

from tidy import config, repos, sync
from tidy.gui.themes import theme_names
from tidy.logger import log_warn

__all__ = ["TidyTray"]


class TidyTray:
    """pystray icon whose menu drives the app's common actions."""

    def __init__(self, show_window, quit_app) -> None:
        self._show_window = show_window
        self._quit_app = quit_app
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            log_warn("no display available — tray disabled")
            return False
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception as exc:  # noqa: BLE001 - tray is optional
            log_warn(f"tray unavailable: {exc}")
            return False

        icon = pystray.Icon(
            "tidy",
            self._make_image(ImageDraw, Image),
            "Tidy",
            menu=self._build_menu(pystray),
        )
        self._icon = icon
        self._thread = threading.Thread(target=icon.run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as exc:  # noqa: BLE001 - already quitting
                log_warn(f"tray stop failed: {exc}")

    @staticmethod
    def _make_image(draw_module, image_module):
        img = image_module.new("1", (16, 16), 0)
        d = draw_module.Draw(img)
        d.rectangle([2, 3, 13, 12], fill=1)  # folder body
        d.rectangle([4, 5, 12, 11], fill=0)  # hole
        d.rectangle([4, 4, 8, 6], fill=1)  # folder tab
        return img

    def _build_menu(self, pystray):
        def backup_all(icon=None, item=None):
            sync.sync_all(config.load())

        def pull_all(icon=None, item=None):
            sync.pull_all(config.load())

        def backup_repo(icon=None, item=None):
            if item is None:
                return
            cfg = config.load()
            repo = repos.find_repo(cfg, item.text)
            if repo is not None:
                sync.sync_repo(cfg, repo)

        def change_theme(icon=None, item=None):
            if item is None:
                return
            cfg = config.load()
            cfg["theme"] = item.text
            config.save(cfg)

        def quit(icon=None, item=None):
            self._quit_app()

        status = self._status_line()
        cfg = config.load()
        items = [
            pystray.MenuItem(f"Tidy — {status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show window", self._show_window, default=True),
            pystray.Menu.SEPARATOR,
        ]
        for repo in cfg["repos"]:
            items.append(pystray.MenuItem(repo["id"], backup_repo))
        items.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Backup all now", backup_all),
                pystray.MenuItem("Pull all", pull_all),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Theme",
                    pystray.Menu(*[pystray.MenuItem(name, change_theme) for name in theme_names()]),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", quit),
            ]
        )
        return pystray.Menu(*items)

    @staticmethod
    def _status_line() -> str:
        stats = config.get_stats(config.load())
        if stats.get("last_error"):
            return "last run failed"
        if stats.get("last_run"):
            return "all synced"
        return "not run yet"
