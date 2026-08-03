"""PyInstaller entry: imports the GUI stack so gi/webkit2 typelibs get bundled,
then runs the Tidy CLI (which dispatches gui / tui / mcp / serve / status…)."""

from __future__ import annotations


def _bootstrap_gi() -> None:
    """Preload GTK3 + WebKit2 4.1 (exactly what pywebview expects) so the
    bundled gi finds the right repository versions — and so PyInstaller's
    static analysis collects the typelibs from this module."""
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GdkPixbuf", "2.0")
        gi.require_version("Soup", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import (  # noqa: F401
            Gdk,
            GdkPixbuf,
            Gio,
            GLib,
            GObject,
            Gtk,
            Soup,
            WebKit2,
        )
    except Exception:  # noqa: BLE001, S110 - intentional: a missing GUI stack must never break the CLI
        pass  # headless machines simply won't have a GUI — CLI still works


_bootstrap_gi()


def main() -> None:
    from tidy.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
