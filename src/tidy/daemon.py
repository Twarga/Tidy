"""Daemon — runs the scheduler 24/7, headless-friendly (VPS or laptop).

``serve()`` guarantees a single instance via a lock file, watches config for
schedule changes, and shuts down cleanly on SIGINT/SIGTERM.
"""

from __future__ import annotations

import fcntl
import os
import signal
import sys
import time
from pathlib import Path

from tidy import config
from tidy.logger import log_info
from tidy.scheduler import SyncScheduler

__all__ = ["acquire_lock", "serve"]

_POLL_SECONDS = 2.0


def acquire_lock() -> Path:
    """Take an exclusive lock; exit if another daemon already owns it."""
    path = config.config_dir() / "tidy.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise SystemExit("another tidy daemon is already running") from None
    return path


class Daemon:
    def __init__(self) -> None:
        self._scheduler = SyncScheduler()
        self._stop = False
        self._last_config_mtime: int | None = None

    # ------------------------------------------------------------- lifecycle

    def run(self) -> int:
        cfg = config.load()
        self._scheduler.reconfigure(cfg)
        self._last_config_mtime = self._config_mtime()
        self._install_signal_handlers()
        log_info("tidy daemon started")
        print("tidy daemon started", flush=True)
        try:
            while not self._stop:
                time.sleep(_POLL_SECONDS)
                if self._config_mtime() != self._last_config_mtime:
                    self._last_config_mtime = self._config_mtime()
                    cfg = config.load()
                    self._scheduler.reconfigure(cfg)
                    log_info("tidy daemon reloaded config")
        finally:
            self._scheduler.shutdown()
            log_info("tidy daemon stopped")
            print("tidy daemon stopped", flush=True)
        return 0

    def _config_mtime(self) -> int:
        path = config.config_path()
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, _frame) -> None:
        self._stop = True


def serve() -> int:
    acquire_lock()  # exits if another daemon is running
    return Daemon().run()


if __name__ == "__main__":
    sys.exit(serve())
