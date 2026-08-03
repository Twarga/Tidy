"""Background execution helpers for the TUI.

Git operations block, so they run on a daemon thread and hand results back
to the caller-provided callback.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

__all__ = ["run_in_background"]


def run_in_background(
    target: Callable[..., object],
    on_done: Callable[[object], None],
    *args: object,
    **kwargs: object,
) -> None:
    """Run ``target(*args, **kwargs)`` in a daemon thread, then ``on_done(result)``."""

    def wrapper() -> None:
        try:
            result = target(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            on_done(exc)
            return
        on_done(result)

    threading.Thread(target=wrapper, daemon=True).start()
