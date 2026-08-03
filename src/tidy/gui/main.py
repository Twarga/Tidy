"""Desktop GUI entry — pywebview pixel window + system tray."""

from __future__ import annotations

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


def _quit_app(window) -> None:
    try:
        window.destroy()
    except Exception as exc:  # noqa: BLE001 - already closing
        log_warn(f"window destroy failed: {exc}")


def main() -> None:
    """Launch the GUI (window + tray). Blocks until the window closes."""
    import webview

    from tidy.gui.tray import TidyTray

    api = Api()
    window = webview.create_window(
        "Tidy",
        url=_asset_url(),
        js_api=api,
        width=880,
        height=780,
        min_size=(620, 560),
    )
    tray = TidyTray(
        show_window=_show_window,
        quit_app=lambda: _quit_app(window),
    )
    tray.start()
    webview.start()
    tray.stop()
