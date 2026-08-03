"""Desktop GUI entry — pywebview pixel window + system tray.

Closing the window hides it to the tray (app keeps running); the tray's
Quit item, SIGTERM and SIGINT all perform a real shutdown.
"""

from __future__ import annotations

import os
import signal
import threading
from pathlib import Path

from tidy.gui.api import Api
from tidy.logger import log_warn


def _asset_url() -> str:
    index = Path(__file__).parent / "web" / "index.html"
    return str(index.resolve())


def _show_window() -> None:
    import webview

    for window in webview.windows:
        window.show()
        window.restore()


def main() -> None:
    """Launch the GUI (window + tray). Blocks until the user quits."""
    import webview

    from tidy.gui.tray import TidyTray

    state = {"allow_close": False}

    def on_closing(window) -> bool | None:
        """Window X clicked → hide to tray instead of quitting."""
        if state["allow_close"]:
            return None  # proceed with close
        window.hide()
        return False  # cancel close

    def _destroy_all() -> None:
        state["allow_close"] = True
        for w in webview.windows:
            try:
                w.destroy()
            except Exception as exc:  # noqa: BLE001 - already closing
                log_warn(f"window destroy failed: {exc}")

    def on_signal(signum, frame) -> None:
        _destroy_all()
        # Safety net if the GTK loop refuses to end.
        threading.Timer(2.0, lambda: os._exit(0)).start()

    def quit_app() -> None:
        _destroy_all()

    api = Api()
    window = webview.create_window(
        "Tidy",
        url=_asset_url(),
        js_api=api,
        width=1120,
        height=720,
        min_size=(940, 620),
    )
    window.events.closing += on_closing
    tray = TidyTray(
        show_window=_show_window,
        quit_app=quit_app,
    )
    tray.start()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    webview.start()
    tray.stop()
